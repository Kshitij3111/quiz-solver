import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from solver.main import solve_quiz
import config


app = FastAPI(title="Quiz Solver")


class Payload(BaseModel):
    email: str
    secret: str
    url: str


@app.post("/")
async def receive(payload: Payload, background_tasks: BackgroundTasks):
# JSON validated by Pydantic — 400 returned automatically on invalid JSON
    if payload.secret != config.QUIZ_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")


# schedule background solving task
    background_tasks.add_task(solve_quiz, payload.email, payload.secret, payload.url)


    return {"status": "accepted", "message": "Quiz processing started"}