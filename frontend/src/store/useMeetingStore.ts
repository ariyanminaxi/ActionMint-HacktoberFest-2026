import {create} from 'zustand';
import type {MeetingSpec,Segment,ActionItem,Decision} from '../api/types';
type Snapshot={spec:MeetingSpec|null};
type State={spec:MeetingSpec|null;segments:Segment[];provider:string;state:string;label:string;error:string|null;undoStack:Snapshot[];redoStack:Snapshot[];setSpec:(s:MeetingSpec)=>void;setSegments:(s:Segment[])=>void;setProgress:(state:string,label:string)=>void;setError:(e:string|null)=>void;editAction:(id:string,patch:Partial<ActionItem>)=>void;editDecision:(id:string,patch:Partial<Decision>)=>void;editTitle:(title:string)=>void;editQuestion:(id:string,text:string)=>void;editRisk:(id:string,text:string)=>void;toggleDone:(id:string)=>void;addAction:()=>void;deleteAction:(id:string)=>void;moveAction:(id:string,direction:-1|1)=>void;mergeAction:(id:string)=>void;undo:()=>void;redo:()=>void;setProvider:(p:string)=>void;reset:()=>void};
const initial={spec:null,segments:[],provider:'',state:'idle',label:'Ready',error:null,undoStack:[] as Snapshot[],redoStack:[] as Snapshot[]};
const snapshot=(spec:MeetingSpec|null):Snapshot=>({spec:spec?structuredClone(spec):null});
export const useMeetingStore=create<State>((set,get)=>({
 ...initial,
 setSpec:(spec)=>set({spec}),setSegments:(segments)=>set({segments}),setProgress:(state,label)=>set({state,label,error:null}),setError:(error)=>set({error}),setProvider:(provider)=>set({provider}),
 editAction:(id,patch)=>set(s=>{if(!s.spec)return s;return {undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,edited:true,action_items:s.spec.action_items.map(a=>a.id===id?{...a,...patch}:a)}}}),
 editDecision:(id,patch)=>set(s=>{if(!s.spec)return s;return {undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,edited:true,decisions:s.spec.decisions.map(d=>d.id===id?{...d,...patch}:d)}}}),
 editTitle:(title)=>set(s=>!s.spec?s:{undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,title,edited:true}}),
 toggleDone:(id)=>{const a=get().spec?.action_items.find(x=>x.id===id);if(a)get().editAction(id,{done:!a.done})},
 addAction:()=>set(s=>{if(!s.spec)return s;return {undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,edited:true,action_items:[...s.spec.action_items,{id:crypto.randomUUID(),task:'New action item',owner:null,due_raw:null,due_iso:null,due_resolved_from_relative:false,note:null,done:false,evidence:[],verified:false,confirmed:true}]}}}),
 deleteAction:(id)=>set(s=>!s.spec?s:{undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,edited:true,action_items:s.spec.action_items.filter(a=>a.id!==id)}}),
 editQuestion:(id,text)=>set(s=>!s.spec?s:{undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,edited:true,open_questions:s.spec.open_questions.map(q=>q.id===id?{...q,text,confirmed:true}:q)}}),
 editRisk:(id,text)=>set(s=>!s.spec?s:{undoStack:[...s.undoStack.slice(-49),snapshot(s.spec)],redoStack:[],spec:{...s.spec,edited:true,risks:s.spec.risks.map(r=>r.id===id?{...r,text,confirmed:true}:r)}}),
 // Reorder keeps the meeting's order in the export: one step per click, undoable like an edit.
 moveAction:(id,direction)=>{const spec=get().spec;if(!spec)return;const index=spec.action_items.findIndex(a=>a.id===id);const target=index+direction;if(index<0||target<0||target>=spec.action_items.length)return;const items=[...spec.action_items];const[item]=items.splice(index,1);items.splice(target,0,item);set({undoStack:[...get().undoStack.slice(-49),snapshot(spec)],redoStack:[],spec:{...spec,edited:true,action_items:items}})},
 // Merge two items: the earlier item keeps its id and position, the later one's evidence and note fold in.
 mergeAction:(id)=>{const spec=get().spec;if(!spec)return;const index=spec.action_items.findIndex(a=>a.id===id);if(index<1)return;const items=[...spec.action_items];const target=items[index-1];const source=items[index];const note=[target.note,source.note,`Merged: ${source.task}`].filter(Boolean).join(' · ');items[index-1]={...target,note,evidence:[...new Set([...target.evidence,...source.evidence])].slice(0,4),confirmed:true};items.splice(index,1);set({undoStack:[...get().undoStack.slice(-49),snapshot(spec)],redoStack:[],spec:{...spec,edited:true,action_items:items}})},
 undo:()=>set(s=>{if(!s.undoStack.length)return s;const prev=s.undoStack[s.undoStack.length-1];return {...prev,undoStack:s.undoStack.slice(0,-1),redoStack:[...s.redoStack,snapshot(s.spec)]}}),
 redo:()=>set(s=>{if(!s.redoStack.length)return s;const next=s.redoStack[s.redoStack.length-1];return {...next,redoStack:s.redoStack.slice(0,-1),undoStack:[...s.undoStack,snapshot(s.spec)]}}),
 reset:()=>set({...initial}),
}));
