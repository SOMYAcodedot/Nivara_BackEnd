"""Normalize assistant reply spacing for a tighter, professional chat UI."""
import re


def compact_assistant_reply(text):
    if not text or not isinstance(text, str):
        return text
    if text.startswith("[Error"):
        return text
    t = text.strip()
    # Collapse 2+ newlines (and spaces between) into one — stops huge gaps in Markdown/React
    t = re.sub(r"(?:\r?\n[\t ]*){2,}", "\n", t)
    return t
