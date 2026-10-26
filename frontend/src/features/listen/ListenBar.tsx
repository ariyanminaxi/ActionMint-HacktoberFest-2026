import {useEffect,useMemo,useRef,useState} from 'react';
import {ChevronDown,Download,Pause,Play,Square,Volume2} from 'lucide-react';
import type {MeetingSpec} from '../../api/types';
import {buildListenScript,buildListenText,DEFAULT_LISTEN_SECTIONS,LISTEN_SECTIONS,type ListenSection} from './script';
import {createSpeaker,listVoices,type Speaker} from './speech';

type Status='idle'|'speaking'|'paused';

function downloadText(name:string,content:string){
  const url=URL.createObjectURL(new Blob([content],{type:'text/plain;charset=utf-8'}));
  const anchor=document.createElement('a');
  anchor.href=url;anchor.download=name;anchor.click();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}

/**
 * Listen bar: reads the reviewed notes aloud with the Web Speech API.
 * Only verified/confirmed items are spoken (same rule as exports), and a `.txt` fallback is always
 * available so the feature degrades honestly in browsers without speech synthesis.
 */
export default function ListenBar({spec}:{spec:MeetingSpec}){
  const supported=typeof window!=='undefined'&&'speechSynthesis' in window;
  const[open,setOpen]=useState(false);
  const[sections,setSections]=useState<Record<ListenSection,boolean>>({...DEFAULT_LISTEN_SECTIONS});
  const[rate,setRate]=useState(1);
  const[voiceURI,setVoiceURI]=useState('');
  const[voices,setVoices]=useState<SpeechSynthesisVoice[]>([]);
  const[status,setStatus]=useState<Status>('idle');
  const speaker=useRef<Speaker|null>(null);

  const lines=useMemo(()=>buildListenScript(spec,sections),[spec,sections]);

  useEffect(()=>{
    if(!supported)return;
    const synth=window.speechSynthesis;
    const load=()=>setVoices(listVoices(synth));
    load();synth.addEventListener?.('voiceschanged',load);
    return()=>synth.removeEventListener?.('voiceschanged',load);
  },[supported]);

  useEffect(()=>()=>{speaker.current?.stop()},[]);

  const getSpeaker=()=>{
    if(!speaker.current)speaker.current=createSpeaker(window.speechSynthesis);
    return speaker.current;
  };

  const play=()=>{
    if(!supported||!lines.length)return;
    if(status==='paused'){window.speechSynthesis.resume();setStatus('speaking');return}
    const chosen=voices.find(voice=>voice.voiceURI===voiceURI)??null;
    getSpeaker().start(lines,{rate,voice:chosen,onDone:()=>setStatus('idle')});
    setStatus('speaking');
  };

  const pause=()=>{window.speechSynthesis.pause();setStatus('paused')};
  const stop=()=>{getSpeaker().stop();setStatus('idle')};

  const toggleSection=(id:ListenSection)=>setSections(current=>({...current,[id]:!current[id]}));

  return <section className={`listen-bar${open?' open':''}`} aria-label="Listen to your notes">
    <div className="listen-main">
      <span className="listen-icon" aria-hidden="true"><Volume2 size={17}/></span>
      <div className="listen-copy">
        <strong>Listen to your notes</strong>
        <small>{supported?`${lines.length} line${lines.length===1?'':'s'} · verified or confirmed items only`:'This browser has no speech support. Download the text instead.'}</small>
      </div>
      <div className="listen-controls">
        {supported&&<button className="button small-button" onClick={status==='speaking'?pause:play} disabled={!lines.length} aria-label={status==='speaking'?'Pause read-out':status==='paused'?'Resume read-out':'Play read-out'}>
          {status==='speaking'?<Pause size={14}/>:<Play size={14}/>} {status==='speaking'?'Pause':status==='paused'?'Resume':'Play'}
        </button>}
        {status!=='idle'&&<button className="outline-button" onClick={stop}><Square size={12}/> Stop</button>}
        <button className="outline-button" onClick={()=>setOpen(value=>!value)} aria-expanded={open} aria-controls="listen-options">Options <ChevronDown size={13}/></button>
      </div>
    </div>
    {open&&<div className="listen-options" id="listen-options">
      <fieldset>
        <legend>Read these sections</legend>
        <div className="listen-checks">{LISTEN_SECTIONS.map(section=><label key={section.id} className="checkbox-line compact"><input type="checkbox" checked={sections[section.id]} onChange={()=>toggleSection(section.id)}/><span>{section.label}</span></label>)}</div>
      </fieldset>
      <label className="listen-select">Speed
        <select value={rate} onChange={event=>setRate(Number(event.target.value))}>
          {[0.8,1,1.2,1.5].map(value=><option key={value} value={value}>{value}×</option>)}
        </select>
      </label>
      <label className="listen-select">Voice
        <select value={voiceURI} onChange={event=>setVoiceURI(event.target.value)} disabled={!voices.length}>
          <option value="">Browser default</option>
          {voices.map(voice=><option key={voice.voiceURI} value={voice.voiceURI}>{voice.name} ({voice.lang})</option>)}
        </select>
      </label>
      <button className="outline-button" onClick={()=>downloadText(`meeting-${spec.meeting_date}-readout.txt`,buildListenText(spec,sections))}><Download size={13}/> Download text</button>
    </div>}
    <p className="listen-status" aria-live="polite">{status==='speaking'?'Reading aloud…':status==='paused'?'Paused.':''}</p>
  </section>;
}
