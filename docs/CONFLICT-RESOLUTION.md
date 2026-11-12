# Merge Conflict Resolution

## What happened

Two feature branches modified `app/main.py` at the same time:

- `feature/conflict-demo`
- `feature/conflict-demo-other`

The first branch added the `/conflict-demo` router.
The second branch added the `/info` router.

When `feature/conflict-demo-other` was updated with the latest `main` branch, Git reported a merge conflict in `app/main.py` because both branches modified the router imports/registration area.

## How it was resolved

The conflict was resolved by keeping both features and registering both routers.

The final `app/main.py` contains both:

- `app.routers.conflict_demo`
- `app.routers.info`

and both routers are registered:

- `/conflict-demo`
- `/info`

## Verification

Run:

```
python -m pytest -v
```

The final result was:

```
13 passed
```

Also `git diff --check` was clean.

## Git history

Document these commits:

- `7c69057` — Add conflict demo endpoint
- `a365544` — Add info endpoint for conflict demo
- `fd240fd` — Resolve merge conflict with main
- `7af5014` — Merge pull request #13

## Result

The conflict was successfully resolved, both features were retained, tests passed, and the resolved changes were merged into protected `main`.
