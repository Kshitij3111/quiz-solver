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
    Full automatic solver:
    - Handles normal quizzes
    - Handles scrape-type quizzes (/demo-scrape, /demo-scrape-data)
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
        # 1. FETCH PAGE (JS-rendered)
        # ----------------------------------------------------------
        try:
            html, resources = await fetch_page_and_context(url)
        except Exception as e:
            print(f"[ERROR] Failed to fetch {url}: {e}")
            return

        # ----------------------------------------------------------
        # 2. PARSE PAGE
        # ----------------------------------------------------------
        quiz = parse_quiz_from_page(html, resources)

        # ----------------------------------------------------------
        # SPECIAL CASE: SCRAPE QUIZ (NO SUBMIT URL)
        # ----------------------------------------------------------
        if quiz.get("scrape_url") and not quiz.get("submit_url"):
            print("[INFO] Detected SCRAPE quiz")

            try:
                scrape_html, _ = await fetch_page_and_context(quiz["scrape_url"])
            except Exception as e:
                print("[ERROR] Failed to fetch scrape-data:", e)
                return

            # Extract the plain secret code
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(scrape_html, "html.parser")
            secret_code = soup.get_text().strip()

            print("[INFO] Scraped secret code:", secret_code)

            # The submit endpoint for scrape quizzes is always this:
            submit_url = "https://tds-llm-analysis.s-anand.net/submit"

            answer_obj = {"answer": secret_code}

            try:
                resp = submit_answer(submit_url, session, answer_obj)
            except Exception as e:
                print("[ERROR] Submission failed:", e)
                return

            print("[INFO] Server response:", resp)

            url = resp.get("url")  # Continue chain
            continue  # Restart loop for next quiz page

        # ----------------------------------------------------------
        # NORMAL QUIZ (has submit_url)
        # ----------------------------------------------------------
        if not quiz.get("submit_url"):
            print("[ERROR] Could not find submit URL on page.")
            return

        # ----------------------------------------------------------
        # 3. PLAN WITH LLM
        # ----------------------------------------------------------
        try:
            plan_struct = await plan_with_llm(quiz, session)
        except Exception as e:
            print(f"[ERROR] LLM planning failed: {e}")
            return

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

        # Fallback direct answer
        if plan_struct.get("answer") is not None:
            answer_obj["answer"] = plan_struct["answer"]

        print("[INFO] Final answer:", answer_obj["answer"])

        # ----------------------------------------------------------
        # 5. SUBMIT
        # ----------------------------------------------------------
        try:
            resp = submit_answer(quiz["submit_url"], session, answer_obj)
        except Exception as e:
            print(f"[ERROR] Submission failed: {e}")
            return

        print("[INFO] Server response:", resp)

        # ----------------------------------------------------------
        # 6. NEXT URL
        # ----------------------------------------------------------
        url = resp.get("url")

    print("\n=== FINISHED QUIZ (or timed out) ===")
