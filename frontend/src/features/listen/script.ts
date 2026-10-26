import type {MeetingSpec} from '../../api/types';

/** Sections the Listen bar can read out. Only verified/confirmed items are ever included. */
export type ListenSection='summary'|'decisions'|'actions'|'questions'|'risks';

export const LISTEN_SECTIONS:{id:ListenSection;label:string}[]=[
  {id:'summary',label:'Summary'},
  {id:'decisions',label:'Decisions'},
  {id:'actions',label:'Actions'},
  {id:'questions',label:'Questions'},
  {id:'risks',label:'Risks'},
];

export const DEFAULT_LISTEN_SECTIONS:Record<ListenSection,boolean>={
  summary:true,decisions:true,actions:true,questions:true,risks:true,
};

// Mirrors the backend default (`verified` defaults to true when a provider omits it).
const accepted=(item:{verified?:boolean;confirmed?:boolean})=>Boolean((item.verified??true)||item.confirmed);

function spokenDate(dueIso:string|null,dueRaw:string|null):string{
  if(dueRaw)return dueRaw;
  if(dueIso)return dueIso;
  return '';
}

/**
 * Pure text builder: one utterance per array entry, in reading order.
 * Keeps the uncertainty rule (C.11) — unverified, unconfirmed items are never spoken.
 */
export function buildListenScript(
  spec:MeetingSpec,
  sections:Record<ListenSection,boolean>=DEFAULT_LISTEN_SECTIONS,
):string[]{
  const lines:string[]=[];
  if(sections.summary){
    if(spec.summary.tldr)lines.push(spec.summary.tldr);
    for(const bullet of spec.summary.bullets)lines.push(bullet);
  }
  if(sections.decisions){
    for(const decision of spec.decisions.filter(accepted)){
      lines.push(`Decision: ${decision.text}${decision.decided_by?` Confirmed by ${decision.decided_by}.`:''}`);
    }
  }
  if(sections.actions){
    for(const action of spec.action_items.filter(accepted)){
      const owner=action.owner?`Owner ${action.owner}.`:'No owner was stated.';
      const due=spokenDate(action.due_iso,action.due_raw);
      lines.push(`Action: ${action.task} ${owner}${due?` Due ${due}.`:' No due date was given.'}${action.done?' Already done.':''}`);
    }
  }
  if(sections.questions){
    for(const question of spec.open_questions.filter(accepted))lines.push(`Open question: ${question.text}`);
  }
  if(sections.risks){
    for(const risk of spec.risks.filter(accepted))lines.push(`Risk: ${risk.text}`);
  }
  return lines.map(line=>line.replace(/\s+/g,' ').trim()).filter(Boolean);
}

/** `.txt` fallback: the same script with the meeting title and a short provenance note. */
export function buildListenText(spec:MeetingSpec,sections:Record<ListenSection,boolean>=DEFAULT_LISTEN_SECTIONS):string{
  const script=buildListenScript(spec,sections);
  const header=`${spec.title} — ${spec.meeting_date}`;
  const note='Read-out of verified or confirmed items only.';
  return [header,note,'',script.join('\n\n'),''].join('\n');
}
