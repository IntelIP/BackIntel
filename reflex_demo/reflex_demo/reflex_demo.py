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
        self.selected_id = row["id"] if row else ""
        self.reason = row["review"]["reason"] if row and row["review"] else ""
        self.decision = row["review"]["decision"] if row and row["review"] else "follow_up"
        self.notice = ""

    @rx.event
    def set_status(self, status: str):
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
            self.cases = read_workspace()["cases"]
            self.error = ""
            row = self._case()
            if row:
                self.selected_id = row["id"]
                self.reason = row["review"]["reason"] if row["review"] else ""
                self.decision = row["review"]["decision"] if row["review"] else "follow_up"
        except (OSError, ValueError):
            self.error = "Could not load the local service. Start the decision API and retry."

    @rx.event
    def select(self, case_id: str):
        self.selected_id = case_id
        self.tab = "finding"
        self.mobile_case = True
        self.notice = ""
        row = self._case()
        if row:
            self.reason = row["review"]["reason"] if row["review"] else ""
            self.decision = row["review"]["decision"] if row["review"] else "follow_up"

    @rx.event
    def choose_workflow(self, workflow: str):
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
        if not row:
            return
        try:
            saved = write_decision(row["id"], self.decision, form_data.get("reason", ""), row["review"]["revision"] if row["review"] else 0, row["evidence"]["sha256"])
            self.cases = [saved if case["id"] == saved["id"] else case for case in self.cases]
            self.status = "all"
            self.selected_id = saved["id"]
            self.reason = saved["review"]["reason"]
            self.notice = "Decision saved. Later outcome is now available."
            self.error = ""
        except (OSError, ValueError) as error:
            self.error = str(error)


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
            rx.el.div(rx.el.span("Same API · Decisions shared with React", class_name="quiet-note"), rx.el.button("Save decision", type="submit", disabled=State.reason.strip() == "", class_name="save-button"), class_name="composer-footer"),
            rx.cond(State.notice != "", rx.el.p(State.notice, role="status", class_name="save-success")),
            rx.cond(State.error != "", rx.el.p(State.error, role="alert", class_name="save-error")), on_submit=State.save, class_name="decision-composer"),
        class_name="reader", aria_label="Selected case",
    )


def index():
    return rx.el.div(
        rx.el.aside(rx.el.div(rx.el.span(rx.icon("sparkles", size=17), class_name="brand-mark"), rx.el.strong("BackIntel"), class_name="brand-row"), rx.el.div("Decision workspace · Python", class_name="navigation-search"),
            rx.el.nav(nav_button("Needs review", "open", "inbox"), nav_button("Reviewed", "reviewed", "circle-check"), nav_button("All cases", "all", "archive")),
            rx.el.div(rx.el.span("Workflows"), rx.el.button("Public issue review", on_click=State.choose_workflow("issues")), rx.el.button("Equipment watch", on_click=State.choose_workflow("equipment")), class_name="nav-section"),
            rx.el.div(rx.el.div("Reflex comparison · Local demo", class_name="demo-note"), class_name="nav-bottom"), class_name="navigation", aria_label="Workspace navigation"),
        rx.el.section(rx.el.header(rx.el.div(rx.el.h2(rx.cond(State.status == "reviewed", "Reviewed", "Cases")), rx.el.span(State.case_count, class_name="list-total")), rx.el.button(rx.icon("refresh-cw", size=16), on_click=State.load, aria_label="Refresh workspace")),
            rx.el.div(rx.el.div(rx.icon("search", size=15), rx.el.input(value=State.query, on_change=State.set_query, placeholder="Search cases", aria_label="Search cases"), class_name="search-field"), class_name="list-filter"),
            rx.el.div(rx.el.select(rx.el.option("Public issue review", value="issues"), rx.el.option("Equipment watch · Simulated", value="equipment"), value=State.workflow, on_change=State.choose_workflow, aria_label="Workflow"), rx.el.select(rx.el.option("Needs review", value="open"), rx.el.option("Reviewed", value="reviewed"), rx.el.option("All cases", value="all"), value=State.status, on_change=State.set_status, aria_label="Review status"), class_name="mobile-controls"),
            rx.el.div("Shared decision records", rx.el.span("Oldest first"), class_name="list-caption"),
            rx.el.div(rx.cond(State.error != "", rx.el.div(State.error, rx.el.button("Retry", on_click=State.load), class_name="queue-message", role="alert")), rx.cond(State.case_count == 0, rx.el.div("No cases here", class_name="queue-message")), rx.foreach(State.visible, queue_row), class_name="case-list-scroll"),
            rx.el.footer("Offline evidence · No model calls"), class_name="case-list", aria_label="Cases"),
        rx.cond(State.case_count > 0, reader(), rx.el.main(rx.el.h1("Decision workspace"), rx.el.p("Choose a workflow or review status."), class_name="reader empty-reader")),
        rx.dialog.root(rx.dialog.content(rx.dialog.title("Source evidence"), rx.dialog.description("Original record used for this finding."), rx.el.div(rx.el.h2(State.current["title"]), rx.el.pre(State.current["evidence"]), rx.cond(State.current["url"] != "", rx.el.a("Open original source ↗", href=State.current["url"], target="_blank", rel="noreferrer")), rx.el.details(rx.el.summary("Record fingerprint"), rx.el.code(State.current["fingerprint"])), class_name="drawer-body"), rx.dialog.close(rx.el.button("Close evidence")), class_name="evidence-drawer", max_width="540px"), open=State.evidence_open, on_open_change=State.set_evidence_open),
        class_name=rx.cond(State.mobile_case, "workspace mobile-case-open", "workspace"),
    )


app = rx.App(stylesheets=["/workspace.css"], theme=rx.theme(appearance="light", accent_color="purple", gray_color="mauve", radius="small"))
app.add_page(index, title="BackIntel · Reflex comparison", on_load=State.load)
