"""Productivity analytics endpoints (owner: Sai).

Intentionally empty: Sai builds this on his own feature branch.

Planned scope:
  * total, completed and pending task counts
  * overdue tasks (pending tasks whose due_date is before today)
  * completion percentage
  * tasks grouped by priority

To start:
  1. Read tasks from the shared store:  from app.store import store
  2. Create `router = APIRouter(prefix="/analytics", tags=["analytics"])` here.
  3. Register it in app/main.py (see the comment there).
  4. Add tests in tests/test_analytics.py.
"""
