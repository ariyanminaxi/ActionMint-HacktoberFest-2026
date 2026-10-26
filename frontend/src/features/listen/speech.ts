/**
 * Minimal, testable queue over the Web Speech API.
 *
 * One utterance at a time: `speak()` is asynchronous in every browser, so the next line is only
 * queued from the previous utterance's `onend`. Errors advance the queue unless they are a
 * deliberate cancel/interrupt. The synth and the utterance factory are injected so the tests can
 * drive it without a DOM.
 */
export type SynthLike={
  speak(utterance:unknown):void;
  cancel():void;
  pause():void;
  resume():void;
};

type SpeakerOptions={rate?:number;voice?:unknown;onDone?:()=>void};

export type Speaker={
  start(lines:string[],options?:SpeakerOptions):void;
  pause():void;
  resume():void;
  stop():void;
  readonly index:number;
  readonly total:number;
};

export function createSpeaker(
  synth:SynthLike,
  makeUtterance:(text:string)=>unknown=(text)=>new SpeechSynthesisUtterance(text),
):Speaker{
  let lines:string[]=[];let index=0;let stopped=false;let options:Required<Omit<SpeakerOptions,'onDone'>>={rate:1,voice:null};
  let onDone:(()=>void)|undefined;

  const finish=()=>{const done=onDone;lines=[];index=0;onDone=undefined;done?.()};

  const speakCurrent=()=>{
    if(stopped)return;
    if(index>=lines.length){finish();return}
    const utterance=makeUtterance(lines[index]) as {
      rate:number;voice:unknown;onend:(()=>void)|null;onerror:((event:{error?:string})=>void)|null;
    };
    utterance.rate=options.rate;
    if(options.voice)utterance.voice=options.voice;
    utterance.onend=()=>{index+=1;speakCurrent()};
    utterance.onerror=event=>{
      if(event?.error==='interrupted'||event?.error==='canceled')return;
      index+=1;speakCurrent();
    };
    synth.speak(utterance);
  };

  return {
    start(next,opts={}){
      synth.cancel();
      lines=[...next];
      index=0;stopped=false;
      options={rate:opts.rate??1,voice:opts.voice??null};
      onDone=opts.onDone;
      if(!lines.length){finish();return}
      speakCurrent();
    },
    pause(){synth.pause()},
    resume(){synth.resume()},
    stop(){stopped=true;lines=[];index=0;onDone=undefined;synth.cancel()},
    get index(){return index},
    get total(){return lines.length},
  };
}

/** Voice list helper: some browsers populate it only after `voiceschanged`. */
export function listVoices(synth:{getVoices?():SpeechSynthesisVoice[]}|null):SpeechSynthesisVoice[]{
  try{return synth?.getVoices?.()??[]}catch{return[]}
}
