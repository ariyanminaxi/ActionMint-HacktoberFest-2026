import {describe,it,expect} from 'vitest';
import {toMarkdown} from './export';
import type {MeetingSpec} from '../api/types';
const spec:MeetingSpec={meeting_id:'12345678',title:'Test sync',meeting_date:'2026-10-26',duration_s:null,source:'transcript',summary:{tldr:'A useful meeting.',bullets:['One point']},topics:[],decisions:[],action_items:[{id:'a',task:'Check the budget',owner:null,due_raw:null,due_iso:null,due_resolved_from_relative:false,note:null,done:false,evidence:['S1'],verified:false,confirmed:false}],open_questions:[],risks:[],follow_ups:{next_meeting:null,notify:[]},attendees:[],edited:true,warnings:[]};
describe('meeting exports',()=>{it('includes the edited state and labels unverified output',()=>{const md=toMarkdown(spec);expect(md).toContain('Test sync');expect(md).toContain('Check the budget (unverified)');expect(md).toContain('Unassigned')})});
