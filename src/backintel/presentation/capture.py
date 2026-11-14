"""Render only BackIntel's installed app in a disposable, loopback-only browser."""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx


@contextlib.contextmanager
def dashboard_server(directory: Path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    # No provider/store credentials or arbitrary app.py from the output directory.
    env = {k: os.environ[k] for k in ("PATH", "HOME", "SYSTEMROOT") if k in os.environ}
    env["BACKINTEL_DASHBOARD_DATA"] = str(directory.resolve() / "dashboard.json")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(__file__).with_name("streamlit_app.py")),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--server.fileWatcherType",
        "none",
    ]
    with (directory / "browser-server.log").open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=log)
        try:
            with httpx.Client(trust_env=False, timeout=1) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Dashboard preview server exited before becoming ready.")
                    try:
                        if client.get(origin + "/_stcore/health").text == "ok":
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise TimeoutError("Dashboard preview server did not become ready.")
            yield origin
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def capture_dashboard(directory: Path, output: Path) -> dict:
    """Capture every reader view at two widths and test the delivered interactions.

    Browser/setup failures raise; they never become a passing visual assessment.
    No model-generated Python, JavaScript, CSS or remote URL is executed.
    """
    from playwright.sync_api import expect, sync_playwright

    from backintel.presentation.design import validate_plan

    data = json.loads((directory / "dashboard.json").read_text())
    plan_path = directory / "presentation.json"
    plan = validate_plan(json.loads(plan_path.read_text()), data) if plan_path.exists() else None
    output.mkdir(parents=True, exist_ok=False)
    evidence = {"views": [], "failures": [], "checks": []}
    with dashboard_server(directory) as origin, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for size, width in (("desktop", 1280), ("mobile", 390)):
                context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1)
                blocked = []

                def route(request, blocked=blocked):
                    url = urlsplit(request.request.url)
                    if f"{url.scheme}://{url.netloc}" == origin or url.scheme in {"data", "blob"}:
                        request.continue_()
                    else:
                        blocked.append(request.request.url.split("?")[0])
                        request.abort()

                context.route("**/*", route)
                page = context.new_page()
                page.on(
                    "pageerror",
                    lambda _, size=size: evidence["failures"].append(f"{size}: browser runtime error"),
                )
                page.goto(origin, wait_until="domcontentloaded")
                page.get_by_text("BackIntel · Analysis", exact=True).wait_for(timeout=30000)
                names = (
                    [s.title for s in plan.sections] + ["Explore", "About the data"]
                    if plan
                    else ["The story", "Explore", "Definitions & limits"]
                )
                for index, name in enumerate(names):
                    if plan:
                        # Navigation itself is exercised, including the mobile overflow menu.
                        link = page.get_by_role("link", name=name, exact=True)
                        expand = page.get_by_role("button", name="Expand sidebar", exact=True)
                        if expand.is_visible():
                            expand.click()
                        if not link.is_visible():
                            more = page.get_by_test_id("stTopNavSection")
                            if more.count():
                                more.last.click()
                        menuitem = page.get_by_role("menuitem", name=name, exact=True)
                        target = menuitem if menuitem.is_visible() else link
                        target.click(timeout=10000)
                        page.get_by_role("heading", name=name, exact=True).wait_for(timeout=15000)
                        collapse = page.get_by_role("button", name="Collapse sidebar", exact=True)
                        if collapse.is_visible():
                            collapse.click()
                    else:
                        page.get_by_role("tab", name=name, exact=True).click()
                    page.locator('[data-testid="stApp"]').wait_for()
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(250)
                    if page.locator('[data-testid="stException"]').count():
                        raise RuntimeError("Streamlit raised an exception while rendering a review view.")
                    expected = (
                        len(plan.sections[index].charts)
                        if plan and index < len(plan.sections)
                        else len(data["charts"])
                        if not plan and index == 0
                        else 0
                    )
                    main = page.locator('[data-testid="stMainBlockContainer"]')
                    if plan:
                        charts = main.locator('[data-testid="stPlotlyChart"]:visible')
                    else:
                        charts = page.get_by_role("tabpanel", name=name).locator(
                            '[data-testid="stPlotlyChart"]:visible'
                        )
                    expect(charts).to_have_count(expected, timeout=15000)
                    if expected:
                        charts.first.locator(".main-svg").first.wait_for(timeout=15000)
                    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
                    if overflow:
                        evidence["failures"].append(f"{size}/{name}: horizontal page overflow")
                    # Streamlit's inner scroller clips element/full-page screenshots. Capture
                    # overlapping real viewports so offscreen content is actually painted.
                    scroller = page.locator('[data-testid="stMain"]')
                    height = scroller.evaluate("e => e.scrollHeight")
                    if height > 16000:
                        raise ValueError(
                            "Dashboard view is too tall to review completely; split it into sections."
                        )
                    viewport = scroller.evaluate("e => e.clientHeight")
                    positions = list(range(0, max(1, height - viewport), max(1, viewport - 100)))
                    positions.append(max(0, height - viewport))
                    for part, position in enumerate(sorted(set(positions)), 1):
                        scroller.evaluate("(e, y) => e.scrollTo(0, y)", position)
                        page.wait_for_timeout(150)
                        filename = f"{size}-{index + 1}-{part}.png"
                        page.screenshot(path=str(output / filename), animations="disabled", timeout=15000)
                        evidence["views"].append(
                            {"name": f"{size}/{name}/{part}", "file": filename, "charts": expected}
                        )
                    scroller.evaluate("e => e.scrollTo(0, 0)")
                    evidence["checks"].append(f"{size}/{name}: navigation and render")
                    if name == "Explore":
                        search = page.get_by_role("textbox", name="Find rows in this table")
                        search.fill("__backintel_no_matching_row_93ad__")
                        search.press("Enter")
                        page.get_by_text("No rows match this view.", exact=True).wait_for(timeout=10000)
                        search.fill("")
                        search.press("Enter")
                        evidence["checks"].append(f"{size}: table search and empty state")
                    if (plan and name == "About the data") or (not plan and index == 0):
                        with page.expect_download() as downloaded:
                            page.get_by_role("button", name="Download analysis").click()
                        path = downloaded.value.path()
                        from openpyxl import load_workbook

                        book = load_workbook(io.BytesIO(Path(path).read_bytes()))
                        for sheet, table in zip(book.worksheets[1:], data["tables"], strict=True):
                            if list(sheet.values)[1:] != [tuple(row) for row in table["rows"]]:
                                evidence["failures"].append(
                                    "Downloaded workbook differs from retained tables"
                                )
                        evidence["checks"].append(f"{size}: workbook download and source values")
                if blocked:
                    evidence["failures"].append(f"{size}: unexpected off-origin resource request")
                context.close()
        finally:
            browser.close()
    (output / "capture.json").write_text(json.dumps(evidence, indent=2))
    return evidence
