"""Browser screenshot service — captures dashboard pages for Discord."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("/tmp/nile-screenshots")  # noqa: S108
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Pages to capture with their target channels
DASHBOARD_PAGES = [
    {"path": "/", "name": "dashboard", "channel": "nile-dashboard"},
    {"path": "/ecosystem", "name": "ecosystem", "channel": "nile-ecosystem"},
    {"path": "/agents", "name": "agents", "channel": "nile-agents"},
    {"path": "/kpis/attacker", "name": "attacker-kpis", "channel": "nile-attacker"},
    {"path": "/kpis/defender", "name": "defender-kpis", "channel": "nile-defender"},
]


async def capture_page(base_url: str, path: str, name: str) -> Path | None:
    """Capture a screenshot of a dashboard page using Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed. Run: playwright install chromium")
        return None

    output_path = SCREENSHOT_DIR / f"{name}.png"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
            page = await browser.new_page(viewport={"width": 1440, "height": 900})

            # Set dark background to match dashboard
            await page.emulate_media(color_scheme="dark")

            url = f"{base_url}{path}"
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for content to render
            await page.wait_for_timeout(2000)

            await page.screenshot(path=str(output_path), full_page=False)
            await browser.close()

            logger.info("Screenshot captured: %s -> %s", url, output_path)
            return output_path

    except Exception:
        logger.exception("Failed to capture screenshot for %s", path)
        return None


async def capture_all_pages(base_url: str) -> dict[str, Path]:
    """Capture screenshots of all dashboard pages."""
    results = {}
    for page_info in DASHBOARD_PAGES:
        path = await capture_page(base_url, page_info["path"], page_info["name"])
        if path:
            results[page_info["name"]] = path
    return results
