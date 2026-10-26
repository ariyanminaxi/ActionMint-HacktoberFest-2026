import {describe,expect,it} from 'vitest';
import {createSpeaker,type SynthLike} from './speech';

type FakeUtterance={text:string;rate:number;voice:unknown;onend:(()=>void)|null;onerror:((event:{error?:string})=>void)|null};

function harness(){
  const spoken:FakeUtterance[]=[];
  const calls={cancel:0,pause:0,resume:0};
  const synth:SynthLike={speak:utterance=>spoken.push(utterance as FakeUtterance),cancel:()=>calls.cancel++,pause:()=>calls.pause++,resume:()=>calls.resume++};
  const speaker=createSpeaker(synth,text=>({text,rate:1,voice:null,onend:null,onerror:null}));
  return {spoken,calls,speaker};
}

describe('speech queue',()=>{
  it('speaks one line at a time and finishes after the last',()=>{
    const {spoken,speaker}=harness();
    let done=0;
    speaker.start(['one','two'],{onDone:()=>done++});
    expect(spoken.map(item=>item.text)).toEqual(['one']);
    spoken[0].onend?.();
    expect(spoken.map(item=>item.text)).toEqual(['one','two']);
    expect(done).toBe(0);
    spoken[1].onend?.();
    expect(done).toBe(1);
  });
  it('applies rate and voice',()=>{
    const {spoken,speaker}=harness();
    const voice={voiceURI:'voice-1'};
    speaker.start(['hello'],{rate:1.5,voice});
    expect(spoken[0].rate).toBe(1.5);
    expect(spoken[0].voice).toBe(voice);
  });
  it('advances past a failed line but not past a deliberate cancel',()=>{
    const {spoken,speaker}=harness();
    speaker.start(['one','two','three']);
    spoken[0].onerror?.({error:'network'});
    expect(spoken[1].text).toBe('two');
    spoken[1].onerror?.({error:'interrupted'});
    expect(spoken).toHaveLength(2); // interrupted means we stopped on purpose
  });
  it('cancels the previous queue on a new start',()=>{
    const {spoken,calls,speaker}=harness();
    speaker.start(['old']);
    speaker.start(['new']);
    expect(calls.cancel).toBe(2); // one cancel per start, so two starts never overlap
    expect(spoken.at(-1)?.text).toBe('new');
  });
  it('stops, pauses and resumes through the synth',()=>{
    const {calls,speaker,spoken}=harness();
    speaker.start(['one','two']);
    speaker.pause();
    speaker.resume();
    speaker.stop();
    expect(calls.pause).toBe(1);
    expect(calls.resume).toBe(1);
    expect(calls.cancel).toBe(2); // start cleared the old queue, stop cleared this one
    spoken[0].onend?.();
    expect(spoken).toHaveLength(1); // no next line after stop
    expect(speaker.total).toBe(0);
  });
  it('finishes immediately for an empty script without speaking',()=>{
    const {spoken,speaker}=harness();
    let done=0;
    speaker.start([],{onDone:()=>done++});
    expect(spoken).toHaveLength(0);
    expect(done).toBe(1);
  });
});
