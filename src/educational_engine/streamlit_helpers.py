"""Helpers to format teaching flow for Streamlit rendering (testable headlessly).

This module provides a pure-function formatter that mirrors how the Streamlit
UI displays the 7-step teaching flow. Tests can call this without importing
Streamlit itself.
"""
from typing import Dict, Any


def format_teaching_flow_for_display(teaching: Dict[str, Any]) -> Dict[str, Any]:
    """Return a mapping of human titles -> string content for each teaching step.

    Falls back to `teaching_answer` or `answer` when specific step keys are missing.
    Lists are joined with newlines.
    """
    steps = [
        ("Intuitive explanation", "step_1_intuitive"),
        ("Real-world example", "step_2_example"),
        ("Technical explanation", "step_3_technical"),
        ("How it works", "step_4_how_it_works"),
        ("Common mistakes", "step_5_mistakes"),
        ("Quick summary", "step_6_summary"),
        ("Understanding check", "step_7_check"),
    ]

    def _to_text(obj: Any) -> str:
        if obj is None:
            return ""
        if isinstance(obj, list):
            return "\n".join(str(x) for x in obj)
        return str(obj)

    fallback = teaching.get("teaching_answer") or teaching.get("answer") or ""

    out = {}
    for title, key in steps:
        content = teaching.get(key)
        if content is None or (isinstance(content, (str, list)) and content == ""):
            content = fallback
        out[title] = _to_text(content)

    out["metadata"] = {
        "teaching_strategy": teaching.get("teaching_strategy"),
        "key_takeaways": teaching.get("key_takeaways"),
        "common_misconceptions": teaching.get("common_misconceptions"),
    }

    return out
