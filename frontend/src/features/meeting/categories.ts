import {AudioLines, Check, CheckCheck, Clock3, FileText, LayoutList, MessageCircle, Users} from 'lucide-react';
import type {LucideIcon} from 'lucide-react';
import type {MeetingSpec} from '../../api/types';

export type CategoryId='overview'|'decisions'|'actions'|'people'|'timeline'|'flow'|'transcript'|'ask'|'recap'|'history';
export type Category={
  id:CategoryId;
  label:string;
  field:keyof MeetingSpec|null;
  frames:readonly [string,string];
  alt:string;
  accent:string;
  icon:LucideIcon;
  visible?:boolean;
};
const record=(id:CategoryId,label:string,field:keyof MeetingSpec|null,alt:string,accent:string,icon:LucideIcon,visible=true):Category=>({id,label,field,frames:[`/assets/categories/${id}-a.png`,`/assets/categories/${id}-b.png`] as const,alt,accent,icon,visible});

export const CATEGORIES:readonly Category[]=[
  record('overview','Overview','summary','Layered rounded shapes','#49c6c3',LayoutList),
  record('decisions','Decisions','decisions','Linked outline shapes','#ff9b78',CheckCheck),
  record('actions','Actions','action_items','Stacked check shapes','#c7f36d',Check),
  record('people','People','attendees','Overlapping circles','#9a9bff',Users),
  record('timeline','Timeline','topics','A dotted curved path','#5bb7f0',Clock3),
  record('flow','Flow','action_items','Connected nodes','#f4b85f',AudioLines,false),
  record('transcript','Transcript',null,'Text lines inside a frame','#73d6c8',FileText),
  record('ask','Ask',null,'A speech bubble and dot','#b9a0ff',MessageCircle),
  record('recap','Recap',null,'A framed spark','#f28fa8',AudioLines),
  record('history','History',null,'A circular arrow','#96b1c9',Clock3,false),
];
export const VISIBLE_CATEGORIES=CATEGORIES.filter(category=>category.visible!==false);
export const getCategory=(id:CategoryId)=>CATEGORIES.find(category=>category.id===id)!;
