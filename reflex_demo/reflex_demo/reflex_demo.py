"""Reflex comparison using shared layout CSS and the same decision API."""
from typing import Any
import reflex as rx
from .client import read_workspace, write_decision


class State(rx.State):
    cases: list[dict[str, Any]] = []
    workflow: str = "issues"
    status: str = "open"
    query: str = ""
    selected_id: str = ""
    reason: str = ""
    decision: str = "follow_up"
    error: str = ""
    notice: str = ""
    evidence_open: bool = False
    mobile_case: bool = False
    tab: str = "finding"
    demo: dict[str, Any] = {}
    show_demo: bool = False
    bound_source: str = ""
    bound_revision: int = 0

    @rx.var
    def source_changed(self) -> bool:
        row = self._case()
        return bool(row and self.bound_source and row["evidence"]["sha256"] != self.bound_source)

    @rx.var
    def evidence_unavailable(self) -> bool:
        return self.demo.get("status") == "unavailable"

    @rx.var
    def demo_active(self) -> bool:
        return bool(self.demo)

    @rx.var
    def demo_header(self) -> dict[str, str]:
        value = self.demo.get("value", {})
        assumptions = value.get("assumptions", {})
        return {"title": self.demo.get("title", ""), "status": self.demo.get("status", ""),
                "problem": self.demo.get("problem", ""), "mode": self.demo.get("jev_mode", ""),
                "capacity": f"{value.get('capacity_hours_per_week', 0):g} hours/week",
                "capacity_value": f"${value.get('capacity_value_usd_per_week', 0):,.2f}/week",
                "assumptions": f"Assumptions: {assumptions.get('cases_per_week', 0)} reports/week; {assumptions.get('manual_minutes_per_case', 0)} minutes manually and {assumptions.get('assisted_minutes_per_case', 0)} minutes assisted; ${assumptions.get('labour_usd_per_hour', 0)}/hour.",
                "explanation": value.get("explanation", ""), "error": self.demo.get("error", ""),
                "comparison_basis": self.demo.get("comparison_basis", ""),
                "local_boundary": self.demo.get("local_rehearsal", {}).get("scope_boundary", ""),
                "local_status": self.demo.get("local_rehearsal", {}).get("status", "")}

    @rx.var
    def demo_workflow_header(self) -> dict[str, str]:
        report = self.demo.get("workflow_rehearsal", {})
        return {"status": report.get("status", ""), "boundary": report.get("scope_boundary", ""),
                "technology": report.get("technology", ""),
                "replay": f"{report.get('pending_triggers', 0)} pending triggers. "
                          f"Replay kept all {report.get('evidence_records', 0)} evidence records unchanged. "
                          "These results belong to the separate simulated rehearsal."}

    @rx.var
    def demo_workflow_rows(self) -> list[dict[str, str]]:
        return [{"name": row["name"], "jobs": str(row["completed_jobs"]),
                 "forecasts": str(row["simulated_predictions"]), "deliveries": str(row["delivery_records"])}
                for row in self.demo.get("workflow_rehearsal", {}).get("scenarios", [])]

    @rx.var
    def demo_local_forecasts(self) -> list[dict[str, str]]:
        rows = []
        for method in self.demo.get("local_rehearsal", {}).get("methods", []):
            for estimate in method["estimates"]:
                rows.append({"queue": estimate["entity"],
                             "method": {"baseline": "Simple baseline", "catboost": "CatBoost", "tabiclv2": "TabICLv2"}[method["route"]],
                             "probability": f"{estimate['value'] * 100:.1f}%",
                             "window": f"simulation windows {estimate['cutoff']}–{estimate['target_at']}"})
        return rows

    @rx.var
    def demo_stages(self) -> list[dict[str, str]]:
        return [{"title": stage["title"], "explanation": stage["explanation"], "technology": stage["technology"],
                 "result": f"{stage['count']} records observed" if stage["count"] else "Not completed" if self.demo.get("status") == "blocked" else "Awaiting execution"}
                for stage in self.demo.get("stages", [])]

    @rx.var
    def demo_models(self) -> list[dict[str, str]]:
        rows = []
        for route, inputs in (("baseline", "structured"), ("catboost", "structured"), ("catboost", "semantic"), ("tabiclv2", "structured"), ("tabiclv2", "semantic")):
            result = next((row for row in self.demo.get("comparisons", []) if row["route"] == route and row["feature_set"] == inputs), None)
            error = result["metrics"].get("brier") if result else None
            rows.append({"method": {"baseline": "Simple baseline", "catboost": "CatBoost", "tabiclv2": "TabICLv2"}[route],
                         "inputs": "Facts + Jev" if inputs == "semantic" else "Facts only",
                         "error": f"{error:.4f}" if error is not None else "Not run",
                         "selected": "Selected for this run" if result and result["selected"] else "Compared" if result else "Pending"})
        return rows

    @rx.var
    def demo_costs(self) -> list[dict[str, str]]:
        value = self.demo.get("value", {})
        rows = [{"label": "Actual provider calls", "value": str(self.demo.get("actual_provider_calls")) if self.demo.get("actual_provider_calls") is not None else "Unknown"}]
        costs = [("Recorded provider charges", value.get("provider_usd")), ("Compute cost", value.get("compute_usd")), ("Net operating benefit", value.get("net_benefit_usd"))]
        attempt = self.demo.get("live_attempt")
        if attempt:
            rows.append({"label": "Retained request attempts", "value": str(attempt["request_attempts"])})
            costs.insert(1, ("Total retained attempt charge", attempt["total_provider_charge_usd"]))
        for label, cost in costs:
            precision = 9 if cost is not None and 0 < abs(cost) < .01 else 2
            rows.append({"label": label, "value": "Unknown" if cost is None else f"${cost:,.{precision}f}"})
        return rows + [{"label": "Measured cash savings", "value": "Not measured"}, {"label": "Attributed revenue gain", "value": "Not measured"}]

    @rx.var
    def demo_today(self) -> list[str]:
        return self.demo.get("today", [])

    @rx.var
    def demo_stack(self) -> list[dict[str, str]]:
        return self.demo.get("stack", [])

    @rx.var
    def demo_boundaries(self) -> list[str]:
        return self.demo.get("boundaries", [])

    def _bind_source(self, row):
        self.bound_source = row["evidence"]["sha256"] if row else ""
        self.bound_revision = row["review"]["revision"] if row and row["review"] else 0

    @rx.var
    def visible(self) -> list[dict[str, str]]:
        return [{"id": row["id"], "title": row["title"], "summary": row["summary"], "date": row["created_at"][:10], "kind": "Simulated" if row["simulated"] else "Public source"} for row in self.cases if row["workflow"] == self.workflow and (self.status == "all" or bool(row["review"]) == (self.status == "reviewed")) and self.query.lower() in (row["id"] + row["title"] + row["summary"]).lower()]

    def _case(self):
        visible = self.visible
        selected = next((row for row in visible if row["id"] == self.selected_id), visible[0] if visible else None)
        return next((row for row in self.cases if selected and row["id"] == selected["id"]), None)

    @rx.var
    def current(self) -> dict[str, str]:
        row = self._case()
        if row is None:
            return {key: "" for key in ("id", "title", "summary", "source_kind", "finding", "finding_status", "facts", "evidence", "url", "fingerprint", "outcome", "prediction", "review_status", "review_reason")}
        return {"id": row["id"], "title": row["title"], "summary": row["summary"], "source_kind": row["source_kind"], "finding": row["finding"]["text"], "finding_status": row["finding"]["status"], "facts": " · ".join(f"{fact['label']}: {fact['value']}" for fact in row["facts"]), "evidence": row["evidence"]["text"], "url": row["evidence"]["url"] or "", "fingerprint": row["evidence"]["sha256"], "outcome": row["outcome"]["text"] if row["outcome"] else "Record your first decision before viewing the later outcome.", "prediction": row["prediction"]["explanation"], "review_status": "Reviewed" if row["review"] else "Needs review", "review_reason": "\n\n".join(f"Revision {review['revision']} · {review['decision'].replace('_', ' ')}\n{review['reason']}" for review in row.get("history", [])) if row["review"] else "No decision recorded."}

    @rx.var
    def case_count(self) -> int:
        return len(self.visible)

    def _sync_selection(self):
        row = self._case()
        self._bind_source(row)
        self.selected_id = row["id"] if row else ""
        self.reason = row["review"]["reason"] if row and row["review"] else ""
        self.decision = row["review"]["decision"] if row and row["review"] else "follow_up"
        self.notice = ""

    @rx.event
    def set_status(self, status: str):
        self.show_demo = False
        self.status = status
        self._sync_selection()
        self.mobile_case = False

    @rx.event
    def set_query(self, query: str):
        self.query = query
        self._sync_selection()

    @rx.event
    def set_reason(self, reason: str):
        self.reason = reason

    @rx.event
    def set_decision(self, decision: str):
        self.decision = decision

    @rx.event
    def set_evidence_open(self, opened: bool):
        self.evidence_open = opened

    @rx.event
    def set_mobile_case(self, opened: bool):
        self.mobile_case = opened

    @rx.event
    def set_tab(self, tab: str):
        self.tab = tab

    @rx.event
    def load(self):
        try:
            selected_id = self.selected_id
            packet = read_workspace()
            if packet.get("demo") and not self.demo:
                self.show_demo = True
            self.demo = packet.get("demo", {})
            self.cases = packet["cases"]
            self.error = ""
            row = self._case()
            if row:
                self.selected_id = row["id"]
                if selected_id != row["id"]:
                    self._sync_selection()
        except (OSError, ValueError):
            self.error = "Could not load the local service. Start the decision API and retry."

    @rx.event
    def select(self, case_id: str):
        self.selected_id = case_id
        self.show_demo = False
        self.tab = "finding"
        self.mobile_case = True
        self.notice = ""
        row = self._case()
        if row:
            self._bind_source(row)
            self.reason = row["review"]["reason"] if row["review"] else ""
            self.decision = row["review"]["decision"] if row["review"] else "follow_up"

    @rx.event
    def choose_workflow(self, workflow: str):
        self.show_demo = False
        self.workflow = workflow
        self.status = "open"
        self.query = ""
        self.selected_id = ""
        self.mobile_case = False
        self.reason = ""
        self.notice = ""

    @rx.event
    def save(self, form_data: dict):
        row = self._case()
        if not row or self.source_changed or self.evidence_unavailable:
            return
        try:
            saved = write_decision(row["id"], self.decision, form_data.get("reason", ""), self.bound_revision, self.bound_source)
            self.cases = [saved if case["id"] == saved["id"] else case for case in self.cases]
            self.status = "all"
            self.selected_id = saved["id"]
            self.reason = saved["review"]["reason"]
            self._bind_source(saved)
            self.notice = "Decision saved. Later outcome is now available." if saved["outcome"] else "Decision saved. No later outcome is available yet."
            self.error = ""
        except (OSError, ValueError) as error:
            self.error = str(error)

    @rx.event
    def refresh_case(self):
        self.load()
        if not self.error:
            self._bind_source(self._case())
            self.notice = "Case refreshed. Review your existing note before saving."

    @rx.event
    def open_demo(self):
        self.show_demo = True
        self.mobile_case = True

    @rx.event
    def close_demo(self):
        self.show_demo = False
        self.mobile_case = False


def nav_button(label, status, icon):
    return rx.el.button(rx.icon(icon, size=17), rx.el.span(label), class_name=rx.cond(State.status == status, "selected", ""), on_click=State.set_status(status))


def queue_row(row):
    return rx.el.button(
        rx.el.div(rx.el.span(row["id"], class_name="row-source"), rx.el.span(row["date"]), class_name="row-meta"),
        rx.el.strong(row["title"]), rx.el.p(row["summary"]), rx.el.span(row["kind"], class_name="row-badge"),
        class_name=rx.cond(State.current["id"] == row["id"], "case-row active", "case-row"), on_click=State.select(row["id"]),
    )


def reader():
    return rx.el.main(
        rx.el.header(rx.el.button(rx.icon("arrow-left", size=18), class_name="mobile-back", on_click=State.set_mobile_case(False), aria_label="Back to cases"), rx.el.span(State.current["id"], class_name="case-number"), rx.el.div(rx.el.button(rx.icon("file-text", size=17), on_click=State.set_evidence_open(True), aria_label="Open evidence"), rx.el.span("H", class_name="reviewer-avatar"), rx.el.button(State.current["review_status"], class_name="review-state", on_click=State.set_tab("activity")), class_name="toolbar-actions"), class_name="case-toolbar"),
        rx.el.div(rx.el.h1(State.current["title"]), rx.el.div(rx.el.span(State.current["source_kind"], class_name="source-tag"), rx.el.span("Reflex comparison", class_name="tag"), class_name="case-tags"), class_name="case-heading"),
        rx.el.div(rx.el.div(rx.foreach([("finding", "Finding"), ("activity", "Decision history"), ("outcome", "Later outcome")], lambda tab: rx.el.button(tab[1], on_click=State.set_tab(tab[0]), custom_attrs={"data-state": rx.cond(State.tab == tab[0], "active", "inactive")})), class_name="tab-list"),
            rx.el.div(rx.cond(State.tab == "finding", rx.el.div(
                rx.el.div(rx.el.div(rx.icon("file-text", size=17), class_name="timeline-icon source"), rx.el.section(rx.el.div(rx.el.strong("Source record"), class_name="record-heading"), rx.el.p(State.current["summary"]), rx.el.button("Read original evidence ↗", on_click=State.set_evidence_open(True), class_name="source-link"), class_name="record-block"), class_name="timeline-row"),
                rx.el.div(rx.el.span(), "Observed facts", rx.el.span(), class_name="timeline-label"),
                rx.el.div(State.current["facts"], class_name="facts-grid"),
                rx.el.div(rx.el.div(rx.icon("sparkles", size=17), class_name="timeline-icon agent"), rx.el.section(rx.el.div(rx.el.strong("BackIntel"), rx.el.span(State.current["finding_status"]), class_name="record-heading"), rx.el.p(State.current["finding"]), class_name="record-block finding-block"), class_name="timeline-row finding-row"),
                rx.el.details(rx.el.summary("Prediction estimates · Experimental"), rx.el.p(State.current["prediction"]), class_name="prediction-details"), class_name="tab-content"),
                rx.el.div(rx.el.h2(rx.cond(State.tab == "outcome", "Later outcome", "Decision history")), rx.el.p(rx.cond(State.tab == "outcome", State.current["outcome"], State.current["review_reason"])), class_name="section-intro")), class_name="reader-scroll"), class_name="case-tabs"),
        rx.el.form(rx.el.div("Your decision", class_name="composer-top"), rx.el.div(rx.foreach([("follow_up", "Follow up"), ("no_action", "No action"), ("need_more_information", "Need more info")], lambda choice: rx.el.button(choice[1], type="button", on_click=State.set_decision(choice[0]), class_name=rx.cond(State.decision == choice[0], "decision-active", ""))), class_name="decision-options"),
            rx.el.label("Reason and next step", html_for="reason", class_name="sr-only"), rx.el.textarea(id="reason", name="reason", value=State.reason, on_change=State.set_reason, placeholder="Add your reason and next step…", max_length=2000, required=True),
            rx.el.div(rx.el.span("Same API · Decisions shared with React", class_name="quiet-note"), rx.el.button("Save decision", type="submit", disabled=(State.reason.strip() == "") | State.source_changed | State.evidence_unavailable, class_name="save-button"), class_name="composer-footer"),
            rx.cond(State.source_changed, rx.el.div("New source information arrived. Your draft is preserved. ", rx.el.button("Refresh case", on_click=State.refresh_case), class_name="save-error", role="alert")),
            rx.cond(State.evidence_unavailable, rx.el.p("Current evidence is unavailable. Saving is disabled until the workspace refreshes.", class_name="save-error", role="alert")),
            rx.cond(State.notice != "", rx.el.p(State.notice, role="status", class_name="save-success")),
            rx.cond(State.error != "", rx.el.div(State.error, rx.el.button("Refresh case", on_click=State.refresh_case), role="alert", class_name="save-error")), on_submit=State.save, class_name="decision-composer"),
        class_name="reader", aria_label="Selected case",
    )


def business_reader():
    return rx.el.main(
        rx.el.header(rx.el.button(rx.icon("arrow-left", size=18), class_name="mobile-back", on_click=State.close_demo, aria_label="Back to cases"), rx.el.span(State.demo_header["status"], class_name="tag"), class_name="case-toolbar"),
        rx.el.div(rx.el.h1(State.demo_header["title"]), rx.el.div(rx.el.span("Synthetic business case", class_name="source-tag"), rx.el.span(State.demo_header["mode"], class_name="tag"), class_name="case-tags"), class_name="case-heading"),
        rx.el.div(rx.el.div(
            rx.cond(State.demo_header["error"] != "", rx.el.p(State.demo_header["error"], role="alert", class_name="save-error")),
            rx.el.section(rx.el.h2("The work being automated"), rx.el.p(State.demo_header["problem"]), rx.el.details(rx.el.summary("How the work is done today"), rx.el.ol(rx.foreach(State.demo_today, lambda step: rx.el.li(step))), class_name="demo-details"), class_name="demo-section"),
            rx.el.section(rx.el.h2("From report to review"), rx.el.p("Stages show recorded evidence. Prepared inputs do not mean that Jev or prediction has run.", class_name="quiet-note"),
                rx.el.ol(rx.foreach(State.demo_stages, lambda stage: rx.el.li(rx.el.div(rx.el.div(rx.el.strong(stage["title"]), rx.el.span(stage["result"]), class_name="record-heading"), rx.el.p(stage["explanation"]), rx.el.span(stage["technology"], class_name="small-label")))), class_name="demo-stages"), class_name="demo-section"),
            rx.cond(State.demo_workflow_header["status"] != "",
                rx.el.section(rx.el.h2("Scheduled workflow rehearsal"), rx.el.p(rx.el.strong(State.demo_workflow_header["status"])),
                    rx.el.p(State.demo_workflow_header["boundary"]), rx.el.span(State.demo_workflow_header["technology"], class_name="small-label"),
                    rx.el.div(rx.el.table(rx.el.thead(rx.el.tr(rx.foreach(["Scenario", "Completed jobs", "Simulated forecasts", "Delivery records"], lambda label: rx.el.th(label, scope="col")))),
                        rx.el.tbody(rx.foreach(State.demo_workflow_rows, lambda row: rx.el.tr(rx.el.th(row["name"], scope="row"), rx.el.td(row["jobs"]), rx.el.td(row["forecasts"]), rx.el.td(row["deliveries"])))), class_name="demo-table"), class_name="demo-table-wrap"),
                    rx.el.p(State.demo_workflow_header["replay"], class_name="quiet-note"), class_name="demo-section")),
            rx.el.section(rx.el.h2("Why compare two prediction models?"), rx.el.p("They are alternatives for the same outcome. Compare facts alone with facts plus interpretation to check whether the extra work adds value."),
                rx.cond(State.demo_header["comparison_basis"] != "", rx.el.p(State.demo_header["comparison_basis"])),
                rx.el.div(rx.el.table(rx.el.thead(rx.el.tr(rx.foreach(["Method", "Inputs", "Probability error", "Run decision"], lambda label: rx.el.th(label, scope="col")))),
                    rx.el.tbody(rx.foreach(State.demo_models, lambda row: rx.el.tr(rx.el.th(row["method"], scope="row"), rx.el.td(row["inputs"]), rx.el.td(row["error"]), rx.el.td(row["selected"])))), class_name="demo-table"), class_name="demo-table-wrap"),
                rx.el.p("Lower probability error is better. Selection uses validation error. Synthetic results do not establish customer accuracy.", class_name="quiet-note"), class_name="demo-section"),
            rx.cond(State.demo_header["local_status"] == "completed",
                rx.el.section(rx.el.h2("What the local models predict"), rx.el.p(State.demo_header["local_boundary"]),
                    rx.el.div(rx.el.table(rx.el.thead(rx.el.tr(rx.foreach(["Queue", "Method", "Chance of next-window breach"], lambda label: rx.el.th(label, scope="col")))),
                        rx.el.tbody(rx.foreach(State.demo_local_forecasts, lambda row: rx.el.tr(rx.el.th(row["queue"], scope="row"), rx.el.td(row["method"]), rx.el.td(row["probability"], rx.el.span(" · ", row["window"], class_name="quiet-note"))))), class_name="demo-table"), class_name="demo-table-wrap"),
                    rx.el.p("These are synthetic examples. They do not establish real customer accuracy or business savings.", class_name="quiet-note"), class_name="demo-section")),
            rx.el.section(rx.el.h2("Value assumptions and execution cost"), rx.el.div(rx.el.div(rx.el.span("Illustrative weekly capacity change"), rx.el.strong(State.demo_header["capacity"])), rx.el.div(rx.el.span("Illustrative weekly labour capacity value"), rx.el.strong(State.demo_header["capacity_value"])), class_name="demo-value"),
                rx.el.p(State.demo_header["assumptions"], class_name="quiet-note"), rx.el.dl(rx.foreach(State.demo_costs, lambda row: rx.el.div(rx.el.dt(row["label"]), rx.el.dd(row["value"]))), class_name="demo-costs"), rx.el.p(State.demo_header["explanation"]), class_name="demo-section"),
            rx.el.details(rx.el.summary("Technology components and their roles"), rx.el.dl(rx.foreach(State.demo_stack, lambda component: rx.el.div(rx.el.dt(component["name"]), rx.el.dd(component["role"]))), class_name="demo-stack"), class_name="demo-details"),
            rx.el.section(rx.el.h2("What this run can establish"), rx.el.ul(rx.foreach(State.demo_boundaries, lambda boundary: rx.el.li(boundary))), rx.el.button("Review the source and record a decision", on_click=State.close_demo), class_name="demo-section"),
            class_name="tab-content demo-content"), class_name="reader-scroll"),
        class_name="reader demo-reader", aria_label="Business workflow demonstration",
    )


def index():
    return rx.el.div(
        rx.el.aside(rx.el.div(rx.el.span(rx.icon("sparkles", size=17), class_name="brand-mark"), rx.el.strong("BackIntel"), class_name="brand-row"), rx.el.div("Decision workspace · Python", class_name="navigation-search"),
            rx.el.nav(rx.cond(State.demo_active, rx.el.button(rx.icon("sparkles", size=17), rx.el.span("Workflow demo"), on_click=State.open_demo)), nav_button("Needs review", "open", "inbox"), nav_button("Reviewed", "reviewed", "circle-check"), nav_button("All cases", "all", "archive")),
            rx.el.div(rx.el.span("Workflows"), rx.el.button(rx.cond(State.demo_active, "Support queues", "Public issue review"), on_click=State.choose_workflow("issues")), rx.cond(State.demo_active == False, rx.el.button("Equipment watch", on_click=State.choose_workflow("equipment"))), class_name="nav-section"),
            rx.el.div(rx.el.div("Reflex comparison · Local demo", class_name="demo-note"), class_name="nav-bottom"), class_name="navigation", aria_label="Workspace navigation"),
        rx.el.section(rx.el.header(rx.el.div(rx.el.h2(rx.cond(State.status == "reviewed", "Reviewed", "Cases")), rx.el.span(State.case_count, class_name="list-total")), rx.el.button(rx.icon("refresh-cw", size=16), on_click=State.load, aria_label="Refresh workspace")),
            rx.el.div(rx.el.div(rx.icon("search", size=15), rx.el.input(value=State.query, on_change=State.set_query, placeholder="Search cases", aria_label="Search cases"), class_name="search-field"), class_name="list-filter"),
            rx.el.div(rx.cond(State.demo_active, rx.el.button("Workflow demo", on_click=State.open_demo), rx.el.select(rx.el.option("Public issue review", value="issues"), rx.el.option("Equipment watch · Simulated", value="equipment"), value=State.workflow, on_change=State.choose_workflow, aria_label="Workflow")), rx.el.select(rx.el.option("Needs review", value="open"), rx.el.option("Reviewed", value="reviewed"), rx.el.option("All cases", value="all"), value=State.status, on_change=State.set_status, aria_label="Review status"), class_name="mobile-controls"),
            rx.el.div("Shared decision records", rx.el.span("Oldest first"), class_name="list-caption"),
            rx.el.div(rx.cond(State.error != "", rx.el.div(State.error, rx.el.button("Retry", on_click=State.load), class_name="queue-message", role="alert")), rx.cond(State.case_count == 0, rx.el.div("No cases here", class_name="queue-message")), rx.foreach(State.visible, queue_row), class_name="case-list-scroll"),
            rx.el.footer(rx.cond(State.demo_active, "Background evidence · " + State.demo_header["status"], "Offline evidence · No model calls")), class_name="case-list", aria_label="Cases"),
        rx.cond(State.show_demo & State.demo_active, business_reader(), rx.cond(State.case_count > 0, reader(), rx.el.main(rx.el.h1("Decision workspace"), rx.el.p("Choose a workflow or review status."), class_name="reader empty-reader"))),
        rx.dialog.root(rx.dialog.content(rx.dialog.title("Source evidence"), rx.dialog.description("Original record used for this finding."), rx.el.div(rx.el.h2(State.current["title"]), rx.el.pre(State.current["evidence"]), rx.cond(State.current["url"] != "", rx.el.a("Open original source ↗", href=State.current["url"], target="_blank", rel="noreferrer")), rx.el.details(rx.el.summary("Record fingerprint"), rx.el.code(State.current["fingerprint"])), class_name="drawer-body"), rx.dialog.close(rx.el.button("Close evidence")), class_name="evidence-drawer", max_width="540px"), open=State.evidence_open, on_open_change=State.set_evidence_open),
        class_name=rx.cond(State.mobile_case, "workspace mobile-case-open", "workspace"),
    )


app = rx.App(stylesheets=["/workspace.css"], theme=rx.theme(appearance="light", accent_color="purple", gray_color="mauve", radius="small"))
app.add_page(index, title="BackIntel · Reflex comparison", on_load=State.load)
