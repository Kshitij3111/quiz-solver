from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin

BASE = "https://tds-llm-analysis.s-anand.net"

def parse_quiz_from_page(html: str, resources: dict):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")

    # Normal submit URL extraction
    submit_url = None
    m = re.search(r"https?://[^\s\"']*submit[^\s\"'>]*", html)
    if m:
        submit_url = m.group(0)

    # Try to parse JSON in <pre>
    pre_json = None
    for pre in soup.find_all("pre"):
        try:
            pre_json = json.loads(pre.get_text().strip())
            break
        except:
            pass

    # Detect scrape instruction
    # Example: "Scrape /demo-scrape-data?email=... (relative ..."
    scrape_match = re.search(
        r"Scrape\s+([^\s]+)\s*\(relative", text, re.IGNORECASE
    )

    scrape_url = None
    if scrape_match:
        relative = scrape_match.group(1)
        scrape_url = urljoin(BASE, relative)

    return {
        "text": text,
        "submit_url": submit_url,
        "scrape_url": scrape_url,
        "raw_html": html,
        "resources": resources,
        "pre_json": pre_json,
    }
