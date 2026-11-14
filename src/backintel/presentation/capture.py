"""Render only BackIntel's installed app in a disposable, loopback-only browser."""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from backintel.presentation.dashboard import streamlit_command


@contextlib.asynccontextmanager
async def dashboard_server(directory: Path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    # No provider/store credentials or arbitrary app.py from the output directory.
    env = {k: os.environ[k] for k in ("PATH", "HOME", "SYSTEMROOT") if k in os.environ}
    env["BACKINTEL_DASHBOARD_DATA"] = str(directory.resolve() / "dashboard.json")
    command = streamlit_command(port)
    with (directory / "browser-server.log").open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=log)
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=1) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Dashboard preview server exited before becoming ready.")
                    try:
                        if (await client.get(origin + "/_stcore/health")).text == "ok":
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise TimeoutError("Dashboard preview server did not become ready.")
            yield origin
        finally:
            if process.poll() is None:
                process.terminate()
                for _ in range(50):
                    if process.poll() is not None:
                        break
                    await asyncio.sleep(0.1)
                else:
                    process.kill()
            process.wait(timeout=5)


def capture_dashboard(directory: Path, output: Path) -> dict:
    """Synchronous entry point for standalone capture."""
    return asyncio.run(capture_dashboard_async(directory, output))


async def _wait_for_charts(charts, expected: int):
    from playwright.async_api import expect

    await expect(charts).to_have_count(expected, timeout=15000)
    for index in range(expected):
        await charts.nth(index).locator(".main-svg").first.wait_for(timeout=15000)


async def capture_dashboard_async(directory: Path, output: Path) -> dict:
    """Capture every reader view at two widths and test the delivered interactions.

    Browser/setup failures raise; they never become a passing visual assessment.
    No model-generated Python, JavaScript, CSS or remote URL is executed.
    """
    from playwright.async_api import async_playwright

    from backintel.presentation.design import validate_plan

    data = json.loads((directory / "dashboard.json").read_text())
    plan_path = directory / "presentation.json"
    plan = validate_plan(json.loads(plan_path.read_text()), data) if plan_path.exists() else None
    output.mkdir(parents=True, exist_ok=False)
    evidence = {"views": [], "failures": [], "checks": []}
    captured_bytes = 0
    async with dashboard_server(directory) as origin, async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            for size, width in (("desktop", 1280), ("mobile", 390)):
                context = await browser.new_context(
                    viewport={"width": width, "height": 900}, device_scale_factor=1
                )
                blocked = []

                async def route(request, blocked=blocked):
                    url = urlsplit(request.request.url)
                    if f"{url.scheme}://{url.netloc}" == origin or url.scheme in {"data", "blob"}:
                        await request.continue_()
                    else:
                        blocked.append(request.request.url.split("?")[0])
                        await request.abort()

                await context.route("**/*", route)
                page = await context.new_page()
                page.on(
                    "pageerror",
                    lambda _, size=size: evidence["failures"].append(f"{size}: browser runtime error"),
                )
                await page.goto(origin, wait_until="domcontentloaded")
                await page.get_by_text("BackIntel · Analysis", exact=True).wait_for(timeout=30000)
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
                        if await expand.is_visible():
                            await expand.click()
                        if not await link.is_visible():
                            more = page.get_by_test_id("stTopNavSection")
                            if await more.count():
                                await more.last.click()
                        menuitem = page.get_by_role("menuitem", name=name, exact=True)
                        target = menuitem if await menuitem.is_visible() else link
                        await target.click(timeout=10000)
                        await page.get_by_role(
                            "heading", name=name, exact=True, level=2 if index < len(plan.sections) else 1
                        ).wait_for(timeout=15000)
                        collapse = page.get_by_role("button", name="Collapse sidebar", exact=True)
                        if await collapse.is_visible():
                            await collapse.click()
                    else:
                        await page.get_by_role("tab", name=name, exact=True).click()
                    await page.locator('[data-testid="stApp"]').wait_for()
                    await page.evaluate("document.fonts.ready")
                    await page.wait_for_timeout(250)
                    if await page.locator('[data-testid="stException"]').count():
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
                    await _wait_for_charts(charts, expected)
                    overflow = await page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
                    if overflow:
                        evidence["failures"].append(f"{size}/{name}: horizontal page overflow")
                    # Streamlit's inner scroller clips element/full-page screenshots. Capture
                    # overlapping real viewports so offscreen content is actually painted.
                    scroller = page.locator('[data-testid="stMain"]')
                    height = await scroller.evaluate("e => e.scrollHeight")
                    viewport = await scroller.evaluate("e => e.clientHeight")
                    positions = list(range(0, max(1, height - viewport), max(1, viewport - 100)))
                    positions.append(max(0, height - viewport))
                    for part, position in enumerate(sorted(set(positions)), 1):
                        if len(evidence["views"]) >= 200:
                            raise ValueError("Dashboard exceeds the 200-screenshot review limit.")
                        await scroller.evaluate("(e, y) => e.scrollTo(0, y)", position)
                        await page.wait_for_timeout(150)
                        filename = f"{size}-{index + 1}-{part}.png"
                        screenshot = await page.screenshot(
                            path=str(output / filename), animations="disabled", timeout=15000
                        )
                        captured_bytes += len(screenshot)
                        if captured_bytes > 24_000_000:
                            raise ValueError("Screenshots exceed the 24 MB review limit.")
                        evidence["views"].append(
                            {"name": f"{size}/{name}/{part}", "file": filename, "charts": expected}
                        )
                    await scroller.evaluate("e => e.scrollTo(0, 0)")
                    evidence["checks"].append(f"{size}/{name}: navigation and render")
                    if name == "Explore":
                        search = page.get_by_role("textbox", name="Find rows in this table")
                        await search.fill("__backintel_no_matching_row_93ad__")
                        await search.press("Enter")
                        await page.get_by_text("No rows match this view.", exact=True).wait_for(timeout=10000)
                        await search.fill("")
                        await search.press("Enter")
                        evidence["checks"].append(f"{size}: table search and empty state")
                    if (plan and name == "About the data") or (not plan and index == 0):
                        async with page.expect_download() as downloaded:
                            await page.get_by_role("button", name="Download analysis").click()
                        path = await (await downloaded.value).path()
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
                await context.close()
        finally:
            await browser.close()
    (output / "capture.json").write_text(json.dumps(evidence, indent=2))
    return evidence
