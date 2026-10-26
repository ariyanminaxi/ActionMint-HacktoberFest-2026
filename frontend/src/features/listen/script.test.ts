import {describe,expect,it} from 'vitest';
import {buildListenScript,buildListenText,type ListenSection} from './script';
import type {MeetingSpec} from '../../api/types';

const spec:MeetingSpec={
  meeting_id:'m1',title:'Launch sync',meeting_date:'2026-10-26',duration_s:null,source:'transcript',
  summary:{tldr:'The launch moved to November 4.',bullets:['QA found two blockers.']},
  topics:[],decisions:[
    {id:'d1',text:'Move the launch to November 4th.',decided_by:'Priya',evidence:['S3'],verified:true,confirmed:false},
    {id:'d2',text:'Guessed decision.',decided_by:null,evidence:[],verified:false,confirmed:false},
  ],
  action_items:[
    {id:'a1',task:'Fix the blockers.',owner:'Anita',due_raw:'by Friday',due_iso:'2026-10-30',due_resolved_from_relative:true,note:null,done:false,evidence:['S4'],verified:true,confirmed:false},
    {id:'a2',task:'Unconfirmed guess.',owner:null,due_raw:null,due_iso:null,due_resolved_from_relative:false,note:null,done:false,evidence:[],verified:false,confirmed:false},
    {id:'a3',task:'Confirmed by hand.',owner:'Rahul',due_raw:null,due_iso:null,due_resolved_from_relative:false,note:null,done:false,evidence:[],verified:false,confirmed:true},
  ],
  open_questions:[{id:'q1',text:'Will pricing show annual discounts?',evidence:['S7'],verified:true,confirmed:false}],
  risks:[{id:'r1',text:'The provider changes its API.',raised_by:'Rahul',evidence:['S10'],verified:true,confirmed:false}],
  follow_ups:{next_meeting:null,notify:[]},attendees:[],edited:false,warnings:[],
};

describe('Listen script',()=>{
  it('speaks the summary first and keeps reading order',()=>{
    const lines=buildListenScript(spec);
    expect(lines[0]).toBe('The launch moved to November 4.');
    expect(lines[1]).toBe('QA found two blockers.');
    expect(lines.some(line=>line.includes('Decision:'))).toBe(true);
    expect(lines.at(-1)).toMatch(/^Risk:/);
  });
  it('never speaks unverified, unconfirmed items',()=>{
    const script=buildListenScript(spec).join(' ');
    expect(script).not.toContain('Guessed decision');
    expect(script).not.toContain('Unconfirmed guess');
    expect(script).toContain('Confirmed by hand');
  });
  it('reads owner, spoken due phrase and note flags honestly',()=>{
    const action=buildListenScript(spec).find(line=>line.startsWith('Action:'));
    expect(action).toContain('Owner Anita.');
    expect(action).toContain('Due by Friday.');
    expect(action).not.toContain('2026-10-30');
  });
  it('honours section checkboxes',()=>{
    const sections:Record<ListenSection,boolean>={summary:false,decisions:false,actions:true,questions:false,risks:false};
    const lines=buildListenScript(spec,sections);
    expect(lines.every(line=>line.startsWith('Action:'))).toBe(true);
    expect(buildListenScript(spec,{...sections,actions:false})).toEqual([]);
  });
  it('builds a text fallback with the title, date and only the chosen lines',()=>{
    const text=buildListenText(spec,{summary:true,decisions:false,actions:false,questions:false,risks:false});
    expect(text).toContain('Launch sync — 2026-10-26');
    expect(text).toContain('The launch moved to November 4.');
    expect(text).not.toContain('Decision:');
  });
});
