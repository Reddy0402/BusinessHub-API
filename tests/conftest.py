"""Test setup: an in-memory SQLite database and no real AI calls.

These variables are set before the app is imported. load_dotenv() never overrides
variables that already exist, so a developer's .env file (with the real Supabase
DATABASE_URL or OpenRouter key) can never be used by the tests.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["OPENROUTER_MODEL"] = ""
