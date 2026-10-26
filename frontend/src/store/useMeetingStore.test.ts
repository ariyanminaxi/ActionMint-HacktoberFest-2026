import {beforeEach,describe,expect,it} from 'vitest';
import {useMeetingStore} from './useMeetingStore';
import {meetingProblems} from '../lib/schema';
import type {ActionItem,MeetingSpec} from '../api/types';

const action=(id:string,task:string,owner:string|null='Anita'):ActionItem=>({id,task,owner,due_raw:null,due_iso:null,due_resolved_from_relative:false,note:null,done:false,evidence:['S1'],verified:false,confirmed:false});
const spec=(items:ActionItem[]):MeetingSpec=>({meeting_id:'m1',title:'Sync',meeting_date:'2026-10-26',duration_s:null,source:'transcript',summary:{tldr:'Summary',bullets:[]},topics:[],decisions:[{id:'d1',text:'Decided.',decided_by:null,evidence:['S1'],verified:true,confirmed:false}],action_items:items,open_questions:[],risks:[],follow_ups:{next_meeting:null,notify:[]},attendees:[],edited:false,warnings:[]});

beforeEach(()=>{useMeetingStore.setState({spec:spec([action('a','First'),action('b','Second'),action('c','Third',null)]),undoStack:[],redoStack:[]})});

describe('meeting review store',()=>{
  it('reorders an action and undoes it',()=>{
    const store=useMeetingStore.getState();
    store.moveAction('a',1);
    expect(useMeetingStore.getState().spec?.action_items.map(a=>a.task)).toEqual(['Second','First','Third']);
    useMeetingStore.getState().undo();
    expect(useMeetingStore.getState().spec?.action_items.map(a=>a.task)).toEqual(['First','Second','Third']);
  });
  it('merges an action into the one above and keeps its evidence',()=>{
    useMeetingStore.getState().mergeAction('b');
    const items=useMeetingStore.getState().spec?.action_items??[];
    expect(items).toHaveLength(2);
    expect(items[0].note).toContain('Merged: Second');
    expect(items[0].evidence).toEqual(['S1']);
    expect(useMeetingStore.getState().spec?.edited).toBe(true);
  });
  it('caps undo at 50 steps',()=>{
    for(let i=0;i<60;i++)useMeetingStore.getState().editTitle(`Title ${i}`);
    expect(useMeetingStore.getState().undoStack).toHaveLength(50);
  });
  it('blocks export while a task is empty and clears the block after a fix',()=>{
    expect(meetingProblems(spec([action('a','First')]))).toEqual([]);
    useMeetingStore.getState().editAction('a',{task:''});
    const problems=meetingProblems(useMeetingStore.getState().spec!);
    expect(problems.some(problem=>problem.includes('Action 1'))).toBe(true);
    useMeetingStore.getState().editAction('a',{task:'Fixed'});
    expect(meetingProblems(useMeetingStore.getState().spec!)).toEqual([]);
  });
  it('turns an edited item into a confirmed one so the check-this badge disappears',()=>{
    expect(useMeetingStore.getState().spec?.action_items[0].confirmed).toBe(false);
    useMeetingStore.getState().editAction('a',{owner:'Priya',confirmed:true});
    expect(useMeetingStore.getState().spec?.action_items[0].confirmed).toBe(true);
  });
});
