from __future__ import annotations
import re

def esc_table(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")

def render_markdown(spec: dict) -> str:
    date=spec.get("meeting_date","—"); title=spec.get("title") or "Meeting notes"
    attendees=", ".join(a.get("name","") for a in spec.get("attendees",[])) or "not stated"
    duration=spec.get("duration_s"); duration_txt=f"{int(duration)//60:02d}:{int(duration)%60:02d}" if duration is not None else "—"
    out=[f"# {title}",f"Date: {date} · Duration: {duration_txt} · Attendees: {attendees}","","## Summary",spec.get("summary",{}).get("tldr","") or "No summary."]
    out += [f"- {b}" for b in spec.get("summary",{}).get("bullets",[])]
    out += ["","## Decisions"]
    for i,d in enumerate(spec.get("decisions",[]),1):
        flag=" (unverified)" if not d.get("verified") and not d.get("confirmed") else ""
        out.append(f"{i}. {d.get('text','')} — decided by {d.get('decided_by') or 'not stated'} [{', '.join(d.get('evidence',[]))}]{flag}")
    out += ["","## Action items","| Done | Task | Owner | Due | Source |","|---|---|---|---|---|"]
    for a in spec.get("action_items",[]):
        flag=" (unverified)" if not a.get("verified") and not a.get("confirmed") else ""
        out.append(f"| {'[x]' if a.get('done') else '[ ]'} | {esc_table(a.get('task',''))}{flag} | {esc_table(a.get('owner') or 'Unassigned')} | {esc_table(a.get('due_iso') or a.get('due_raw') or '—')} | {', '.join(a.get('evidence',[]))} |")
    for key,label in (("open_questions","Open questions"),("risks","Risks")):
        out += ["",f"## {label}"]
        out += [f"- {x.get('text','')} [{', '.join(x.get('evidence',[]))}]" for x in spec.get(key,[])] or ["- None recorded."]
    fu=spec.get("follow_ups",{})
    out += ["","## Follow-ups",f"Next meeting: {fu.get('next_meeting') or 'not stated'} · Notify: {', '.join(fu.get('notify',[])) or 'not stated'}","","## Flow","```mermaid","graph LR"]
    for i,a in enumerate(spec.get("action_items",[]),1):
        owner=(a.get("owner") or "Unassigned").replace('"',"'").replace("[", "(").replace("]", ")").replace("\n"," ")[:40]
        task=(a.get("task") or "task").replace('"',"'").replace("[", "(").replace("]", ")").replace("\n"," ")[:40]
        out.append(f'  O{i}["{owner}"] --> T{i}["{task}"]')
    out += ["```",""]
    return "\n".join(out)
