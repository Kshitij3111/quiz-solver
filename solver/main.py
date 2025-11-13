import asyncio
import time
import os
from typing import Dict, Any

from .fetch import fetch_page_and_context
from .parse import parse_quiz_from_page
from .llm_agent import plan_with_llm
from .executor import execute_plan
from .submit import submit_answer
import config


async def solve_quiz(email: str, secret: str, start_url: str):
    """
    Full solver loop:
    1. Fetch page
    2. Parse quiz instructions
    3. LLM generates a structured plan
    4. Execute plan (download → extract → compute)
    5. Submit answer
    6. Follow next URL until no more or timeout
    """

    deadline = time.time() + config.QUIZ_TIMEOUT_SECONDS
    url = start_url

    session = {
        "email": email,
        "secret": secret,
        "current_url": start_url,
    }

    working_dir = os.path.join(os.getcwd(), ".quiz_work")
    os.makedirs(working_dir, exist_ok=True)

    while url and time.time() < deadline:
        session["current_url"] = url
        print(f"\n--- Solving quiz: {url} ---")

        # ----------------------------------------------------------
        # 1. FETCH PAGE (Playwright JS-rendered)
        # ----------------------------------------------------------
        try:
            html, resources = await fetch_page_and_context(url)
        except Exception as e:
            print(f"[ERROR] Failed to fetch {url}: {e}")
            return

        # ----------------------------------------------------------
        # 2. PARSE PAGE (extract submit_url, links, atob, pre_json)
        # ----------------------------------------------------------
        quiz = parse_quiz_from_page(html, resources)

        if not quiz.get("submit_url"):
            print("[ERROR] Could not find submit URL on page.")
            return

        # ----------------------------------------------------------
        # 3. PLAN WITH LLM (or fallback)
        # ----------------------------------------------------------
        try:
            plan_struct = await plan_with_llm(quiz, session)
        except Exception as e:
            print(f"[ERROR] LLM planning failed: {e}")
            return

        # plan_struct contains:
        # { "plan": {"steps": [...]}, "answer": maybe_final, "explain": ... }

        plan = plan_struct.get("plan", {})
        print("[INFO] Generated plan:", plan)

        # ----------------------------------------------------------
        # 4. EXECUTE PLAN
        # ----------------------------------------------------------
        try:
            answer_obj = await execute_plan(plan, session, working_dir)
        except Exception as e:
            print(f"[ERROR] Plan execution failed: {e}")
            return

        # If LLM already produced direct answer (rare)
        if plan_struct.get("answer") is not None:
            answer_obj["answer"] = plan_struct["answer"]

        print("[INFO] Final answer:", answer_obj["answer"])

        # ----------------------------------------------------------
        # 5. SUBMIT ANSWER
        # ----------------------------------------------------------
        try:
            resp = submit_answer(quiz["submit_url"], session, answer_obj)
        except Exception as e:
            print(f"[ERROR] Submission failed: {e}")
            return

        print("[INFO] Server response:", resp)

        # ----------------------------------------------------------
        # 6. NEXT URL OR END
        # ----------------------------------------------------------
        url = resp.get("url")  # None means quiz is complete

    print("\n=== FINISHED QUIZ (or timed out) ===")
