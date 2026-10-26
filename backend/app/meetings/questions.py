from __future__ import annotations
from pathlib import Path
import re

DEFAULT_PATH=Path(__file__).resolve().parents[2]/"data"/"questions.md"

def parse_questions(path: Path=DEFAULT_PATH) -> dict[str,list[dict[str,str]]]:
    text=path.read_text(encoding="utf-8")
    categories: dict[str,list[dict[str,str]]]={}
    category=None; current=None
    for line in text.splitlines():
        if line.startswith("## "):
            category=line[3:].strip(); categories.setdefault(category,[]); current=None
        elif line.startswith("### ") and category:
            qid=line[4:].strip()
            if any(q.get("id")==qid for values in categories.values() for q in values): raise ValueError(f"Duplicate question id: {qid}")
            current={"id":qid,"ask":"","rule":""}; categories[category].append(current)
        elif current and line.startswith("ask:"):
            current["ask"]=line[4:].strip()
        elif current and line.startswith("rule:"):
            current["rule"]=line[5:].strip()
    if any(not q["ask"] or not q["rule"] for group in categories.values() for q in group): raise ValueError("Each question requires ask and rule lines")
    return categories
