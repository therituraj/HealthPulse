"""Vercel entry point. Vercel looks for the module-level `app` object."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _app import create_app  # noqa: E402  ("_app" is ignored by Vercel as a function route)

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
