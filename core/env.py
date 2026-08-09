"""
core/env.py — Environment variable helpers.
"""

import os
import sys


def require_key(name: str, hint: str = "") -> str:
    """
    Return an API key from the environment or exit with a clear message.
    """
    val = os.environ.get(name, "").strip()
    if not val or val.startswith("your_"):
        print(f"\n  Missing API key: {name}")
        print(f"  Copy .env.example to .env and set {name}.")
        if hint:
            print(f"  {hint}")
        sys.exit(1)
    return val
