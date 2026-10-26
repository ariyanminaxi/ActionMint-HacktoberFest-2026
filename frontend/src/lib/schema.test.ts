import {describe,it,expect} from 'vitest';
import {actionSchema,safeUrlSchema} from './schema';
const good={id:'a',task:'Send notes',owner:null,due_raw:null,due_iso:null,due_resolved_from_relative:false,note:null,done:false,evidence:[],verified:false,confirmed:true};
describe('schemas',()=>{it('accepts a user-authored action with no transcript evidence',()=>{expect(actionSchema.safeParse(good).success).toBe(true)});it('rejects custom insecure API URLs',()=>{expect(safeUrlSchema.safeParse('javascript:alert(1)').success).toBe(false);expect(safeUrlSchema.safeParse('http://localhost:8000').success).toBe(true)})});
