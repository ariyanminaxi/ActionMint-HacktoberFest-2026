from __future__ import annotations
import re
from app.meetings.dates import resolve_due_date

STOP = {"the","a","an","to","and","or","of","in","on","by","for","with","is","are","was","were","will","i","we","you","he","she","they","it","this","that","be","do","does","should","can","could","please","once","after"}
def words(value: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9]+", value) if w.lower() not in STOP and len(w)>1}

def verify_spec(spec: dict, segments: list[dict]) -> dict:
    by_id = {s["id"]: s for s in segments}
    attendees = {a.get("name","").casefold() for a in spec.get("attendees",[])}
    warnings = list(spec.get("warnings",[]))
    for category in ("decisions","action_items","open_questions","risks"):
        for item in spec.get(category,[]):
            ids = [i for i in item.get("evidence",[]) if i in by_id][:4]
            item["evidence"] = ids
            source = " ".join(by_id[i]["text"] for i in ids)
            original = words(item.get("text") or item.get("task") or "")
            overlap = len(original & words(source)) / max(1,len(original))
            verified = bool(ids) and overlap >= .40
            owner = item.get("owner")
            if owner and owner.casefold() not in source.casefold() and owner.casefold() not in attendees:
                item["owner"] = None
                item["note"] = (item.get("note") + " · " if item.get("note") else "") + "owner not stated"
                verified = False
            raw = item.get("due_raw")
            if raw and raw.casefold() not in source.casefold():
                item["due_raw"] = None; item["due_iso"] = None
                verified = False
            if raw and item.get("due_raw"):
                item["due_iso"], item["due_resolved_from_relative"] = resolve_due_date(raw, spec["meeting_date"])
            item["verified"] = bool(item.get("verified", True) and verified)
            if not item["verified"]:
                warnings.append(f"{category[:-1].replace('_',' ').title()} needs review: evidence could not be fully verified")
    spec["warnings"] = list(dict.fromkeys(warnings))
    return spec
