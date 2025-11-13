import os


QUIZ_SECRET = os.getenv("QUIZ_SECRET", "Kangaroo")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# timeouts
QUIZ_TIMEOUT_SECONDS = int(os.getenv("QUIZ_TIMEOUT_SECONDS", "170")) # keep <180