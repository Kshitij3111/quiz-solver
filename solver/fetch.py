# Uses Playwright to render the page and return HTML and downloaded resources
from playwright.async_api import async_playwright
import asyncio
import re
import os
import httpx


async def fetch_page_and_context(url: str, timeout: int = 30):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until='networkidle', timeout=timeout*1000)


        # grab rendered HTML
        html = await page.content()


        # attempt to collect common inline JSON or pre elements
        resources = {}
        pre_handles = await page.query_selector_all('pre')
        if pre_handles:
            resources['pre_texts'] = [await h.inner_text() for h in pre_handles]


        # collect script tags for atob patterns
        script_handles = await page.query_selector_all('script')
        scripts = []
        for h in script_handles:
            txt = await h.inner_text()
            scripts.append(txt)
        resources['scripts'] = scripts


        # find links (pdf/csv) from DOM
        links = await page.query_selector_all('a')
        hrefs = []
        for a in links:
            try:
                href = await a.get_attribute('href')
                if href:
                    hrefs.append(href)
            except Exception:
                continue
        resources['links'] = hrefs

        await browser.close()
        return html, resources

async def download_resource(url: str, dest_dir: str) -> str:
    """Download a resource to dest_dir and return local path (sync over httpx async)."""
    os.makedirs(dest_dir, exist_ok=True)
    filename = os.path.basename(url.split('?')[0]) or 'resource'
    local = os.path.join(dest_dir, filename)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            with open(local, 'wb') as f:
                f.write(r.content)
        return local
    except Exception:
        import requests
        r = requests.get(url)
        r.raise_for_status()
        with open(local, 'wb') as f:
            f.write(r.content)
        return local