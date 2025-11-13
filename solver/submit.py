import requests
import json
from typing import Dict, Any


def submit_answer(submit_url: str, session: Dict[str, Any], answer_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends the computed answer to the quiz server.
    The server returns:
        {
            "correct": true/false,
            "url": next_quiz_url_or_null,
            "reason": optional_string
        }
    """

    payload = {
        "email": session["email"],
        "secret": session["secret"],
        "url": session.get("current_url"),   # the quiz page we just solved
        "answer": answer_obj.get("answer"),
    }

    # optional attachments (base64 files, images, etc.)
    if answer_obj.get("attachments"):
        payload["attachments"] = answer_obj["attachments"]

    headers = {"Content-Type": "application/json"}

    try:
        res = requests.post(submit_url, json=payload, headers=headers, timeout=20)
        res.raise_for_status()
    except Exception as e:
        return {
            "correct": False,
            "url": None,
            "reason": f"Submit failed: {str(e)}"
        }

    # Try parsing JSON safely
    try:
        return res.json()
    except Exception:
        return {
            "correct": False,
            "reason": f"Non-JSON response from server: {res.text}",
            "url": None
        }
