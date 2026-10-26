import {z} from 'zod';
import type {MeetingSpec} from '../api/types';

const isoDate=z.string().regex(/^\d{4}-\d{2}-\d{2}$/,'Use YYYY-MM-DD');
export const actionSchema=z.object({
  id:z.string().min(1),
  task:z.string().min(1,'An action needs a task.').max(200,'Keep the task under 200 characters.'),
  owner:z.string().max(80,'Keep the owner under 80 characters.').nullable(),
  due_raw:z.string().nullable(),
  due_iso:isoDate.nullable(),
  due_resolved_from_relative:z.boolean(),
  note:z.string().nullable(),
  done:z.boolean(),
  evidence:z.array(z.string()).max(4),
  verified:z.boolean(),
  confirmed:z.boolean(),
});
export const decisionSchema=z.object({
  id:z.string().min(1),
  text:z.string().min(1,'A decision needs text.').max(240,'Keep the decision under 240 characters.'),
  decided_by:z.string().nullable(),
  evidence:z.array(z.string()).max(4),
  verified:z.boolean(),
  confirmed:z.boolean(),
});
export const questionSchema=z.object({id:z.string().min(1),text:z.string().min(1,'An open question needs text.').max(200),evidence:z.array(z.string()),verified:z.boolean(),confirmed:z.boolean()});
export const riskSchema=z.object({id:z.string().min(1),text:z.string().min(1,'A risk needs text.').max(200),raised_by:z.string().nullable(),evidence:z.array(z.string()),verified:z.boolean(),confirmed:z.boolean()});
export const safeUrlSchema=z.string().url().refine(v=>{try{const u=new URL(v);return (u.protocol==='https:'||((u.protocol==='http:')&&['localhost','127.0.0.1'].includes(u.hostname)))&&!u.username&&!u.password}catch{return false}},{message:'Use HTTPS, or localhost for local development.'});

/**
 * Everything that must be fixed before an export can be produced (C.10/C.11).
 * Returns human-readable reasons, in the order the user sees them on screen.
 */
export function meetingProblems(spec:MeetingSpec):string[]{
  const problems:string[]=[];
  if(!spec.title.trim())problems.push('The meeting title is empty.');
  if(spec.title.length>120)problems.push('The meeting title is longer than 120 characters.');
  spec.decisions.forEach((decision,index)=>{
    const parsed=decisionSchema.safeParse(decision);
    if(!parsed.success)problems.push(`Decision ${index+1}: ${parsed.error.issues[0]?.message??'invalid'}`);
  });
  spec.action_items.forEach((action,index)=>{
    const parsed=actionSchema.safeParse(action);
    if(!parsed.success)problems.push(`Action ${index+1}: ${parsed.error.issues[0]?.message??'invalid'}`);
  });
  spec.open_questions.forEach((question,index)=>{
    if(!questionSchema.safeParse(question).success)problems.push(`Open question ${index+1}: add text or delete it.`);
  });
  spec.risks.forEach((risk,index)=>{
    if(!riskSchema.safeParse(risk).success)problems.push(`Risk ${index+1}: add text or delete it.`);
  });
  const ids=spec.action_items.map(action=>action.id);
  if(new Set(ids).size!==ids.length)problems.push('Two actions share an id; reload the meeting.');
  return problems;
}
