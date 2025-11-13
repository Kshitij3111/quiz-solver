# Lightweight parsing helpers: extract question text, submit URL, any base64 attachments
from bs4 import BeautifulSoup
import re
import json
import base64




def _extract_atob_from_scripts(scripts):
    results = []
    pat = re.compile(r"atob\((?:'|\")([A-Za-z0-9+/=\n]+)(?:'|\")\)")
    for s in scripts:
        for m in pat.finditer(s):
            results.append(m.group(1))
    return results

def parse_quiz_from_page(html: str, resources: dict):
    soup = BeautifulSoup(html, 'html.parser')


    # get visible text
    text = soup.get_text(separator='\n')


    # try to extract submit URL from <span class="origin"> or any /submit occurrence
    submit_url = None
    span = soup.find('span', class_='origin')
    if span:
        submit_url = span.get_text(strip=True) + '/submit'


    if not submit_url:
        m = re.search(r"https?://[\w\.-]+/submit[\w/-]*", html)
        if m:
            submit_url = m.group(0)


    # extract JSON from <pre>
    pre_json = None
    if resources.get('pre_texts'):
        for t in resources['pre_texts']:
            try:
                pre_json = json.loads(t)
                break
            except Exception:
                continue

    # extract atob content from scripts
    atobs = []
    if resources.get('scripts'):
        atobs = _extract_atob_from_scripts(resources['scripts'])

    decoded_atobs = []
    for a in atobs:
        try:
            decoded = base64.b64decode(a).decode('utf-8', errors='ignore')
            decoded_atobs.append(decoded)
        except Exception:
            continue


    # collect links
    links = resources.get('links', [])


    return {
    'text': text,
    'submit_url': submit_url,
    'pre_json': pre_json,
    'atob_decoded': decoded_atobs,
    'links': links,
    'raw_html': html,
    'resources': resources,
    }