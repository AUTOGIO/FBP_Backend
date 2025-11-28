# FBP Quality Pipeline Rule

After any file is saved:
1. Run Ruff (with --fix)
2. Run mypy on app/
3. Run pytest (fast modules only)
4. Run static startup import check
5. Mark issues and propose fixes automatically

If a fix is unsafe, ask for confirmation.

