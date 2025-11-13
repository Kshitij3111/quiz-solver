import os
import json
import asyncio
from typing import Dict, Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --------------------------------------------------------
# LOW-LEVEL OPENAI CALL
# --------------------------------------------------------
async def _call_openai(prompt: str) -> str:
    import openai
    openai.api_key = OPENAI_API_KEY

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a strict JSON-only data analysis agent."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return resp.choices[0].message["content"]

    except Exception as e:
        return json.dumps({
            "error": f"OpenAI failure: {str(e)}",
            "plan": {"steps": []},
            "answer": None,
        })

# --------------------------------------------------------
# DETERMINISTIC NON-LLM FALLBACK
# --------------------------------------------------------
async def _fallback_planner(quiz: Dict[str, Any]) -> Dict[str, Any]:
    text = quiz.get("text") or quiz.get("url_text") or ""
    links = quiz.get("links", [])
    pre_json = quiz.get("pre_json")

    # 1) If quiz gives JSON template
    if pre_json:
        return {
            "plan": {"steps": [
                {"action": "return_value", "value": pre_json.get("answer", "anything")}
            ]},
            "answer": pre_json.get("answer", "anything"),
            "explain": "Used <pre> JSON template",
        }

    # 2) If PDF exists
    pdfs = [x for x in links if x.lower().endswith(".pdf")]
    if pdfs:
        return {
            "plan": {
                "steps": [
                    {"action": "download", "url": pdfs[0]},
                    {"action": "extract_pdf_table", "path": None, "page": 1},
                    {"action": "sum_column", "column": "value"},
                ]
            },
            "answer": None,
            "explain": "Fallback PDF heuristic",
        }

    # 3) Fallback numeric extraction
    import re
    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", text)
    if nums:
        return {
            "plan": {"steps": [{"action": "return_value", "value": nums[0]}]},
            "answer": nums[0],
            "explain": "Returned first detected number",
        }

    # 4) Final fallback
    return {
        "plan": {"steps": [{"action": "return_value", "value": "anything"}]},
        "answer": "anything",
        "explain": "Generic fallback",
    }

# --------------------------------------------------------
# MAIN ENTRYPOINT – RETURN PLAN + ANSWER
# --------------------------------------------------------
async def plan_with_llm(quiz: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    # no API key → fallback
    if not OPENAI_API_KEY:
        return await _fallback_planner(quiz)

    prompt = f"""
You solve data quizzes. ALWAYS output valid JSON only.

Quiz text:
-----
{quiz.get('text')}
-----
Links: {quiz.get('links')}
PRE JSON: {quiz.get('pre_json')}
Decoded base64: {quiz.get('atob_decoded')}

Return exactly this JSON:
{{
  "plan": {{
      "steps": [
          {{"action": "download" | "extract_pdf_table" | "extract_html_table" |
            "sum_column" | "return_value" | "submit_base64_plot"}}
      ]
  }},
  "answer": <value or null>,
  "explain": <optional>
}}
NO text outside JSON.
"""

    raw = await _call_openai(prompt)

    try:
        out = json.loads(raw)

        if "plan" not in out:
            out["plan"] = {"steps": []}
        if "steps" not in out["plan"]:
            out["plan"]["steps"] = []
        if "answer" not in out:
            out["answer"] = None

        return out

    except Exception:
        return {
            "plan": {"steps": []},
            "answer": raw,
            "explain": "LLM returned invalid JSON; wrapped raw output",
        }
