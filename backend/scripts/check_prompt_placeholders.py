#!/usr/bin/env python3
"""Verify a prompt file's placeholder set against an expected set, and report
word count. Usage:
    python -m scripts.check_prompt_placeholders <slug> {expected,...}
Exits non-zero if the placeholder set differs."""
from __future__ import annotations
import re
import sys
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent.parent / "agents" / "prompts"


def placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{[a-zA-Z_]+\}", text))


def main() -> int:
    slug = sys.argv[1]
    expected = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else set()
    text = (PROMPTS / f"{slug}.txt").read_text()
    found = placeholders(text)
    words = len(text.split())
    print(f"{slug}: words={words} placeholders={sorted(found)}")
    if expected and found != expected:
        print(f"  MISMATCH expected={sorted(expected)} got={sorted(found)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
