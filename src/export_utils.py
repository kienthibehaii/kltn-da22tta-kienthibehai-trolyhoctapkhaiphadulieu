"""
export_utils.py
───────────────
Export conversations to PDF, Markdown, etc.
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime

def export_to_markdown(chat_history: List[Dict], filename: str = None) -> str:
    """Export chat to Markdown format"""

    if filename is None:
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    markdown = "# Conversation Export\n\n"
    markdown += f"*Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

    for msg in chat_history:
        role = msg.get("role", "user").title()
        content = msg.get("content", "")
        markdown += f"## {role}\n\n{content}\n\n---\n\n"

    # Save to file
    output_path = Path("exports") / filename
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return str(output_path)


def export_to_txt(chat_history: List[Dict], filename: str = None) -> str:
    """Export chat to plain text"""

    if filename is None:
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    text = "CONVERSATION LOG\n"
    text += f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    text += "=" * 70 + "\n\n"

    for msg in chat_history:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        text += f"[{role}]\n{content}\n\n"

    # Save to file
    output_path = Path("exports") / filename
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    return str(output_path)


def format_for_display(chat_history: List[Dict]) -> str:
    """Format chat history for Streamlit display"""
    formatted = ""
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        formatted += f"\n**{role.title()}**: {content}\n"
    return formatted
