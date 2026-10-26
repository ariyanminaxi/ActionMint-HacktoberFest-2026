import type {MeetingSpec,Segment} from './types';

const base=(import.meta.env.VITE_API_BASE as string|undefined)?.replace(/\/$/,'') ?? '';
const appToken=()=>typeof sessionStorage==='undefined'?'':sessionStorage.getItem('actionmint.appToken')||sessionStorage.getItem('morrow.appToken')||'';
const sessionToken=(id:string)=>typeof sessionStorage==='undefined'?'':sessionStorage.getItem(`actionmint.session.${id}`)||sessionStorage.getItem(`morrow.session.${id}`)||'';
export function setSessionToken(id:string,token:string){sessionStorage.setItem(`actionmint.session.${id}`,token)}
export function setAppToken(token:string){sessionStorage.setItem('actionmint.appToken',token)}
export function getAppToken(){return appToken()}
export function clearSessionToken(id:string){sessionStorage.removeItem(`actionmint.session.${id}`);sessionStorage.removeItem(`morrow.session.${id}`)}

async function request<T>(path:string,init:RequestInit={},id?:string):Promise<T>{
  const headers=new Headers(init.headers); headers.set('X-App-Token',appToken());
  if(id) headers.set('X-Session-Token',sessionToken(id));
  if(init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type','application/json');
  const response=await fetch(`${base}${path}`,{...init,headers});
  if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=body?.detail?.message||body?.detail||message}catch{/* Error bodies may not be JSON. */};throw new Error(String(message))}
  return response.json() as Promise<T>;
}
export async function getHealth(){return request<{status:string;providers:{name:string;ok:boolean;latency_ms:number|null}[];default_provider:string;model:string;history:{configured:boolean}}>('/health')}
export async function createMeeting(input:{source:'transcript'|'upload'|'link';title?:string;meeting_date?:string;text?:string}){
  const result=await request<{meeting_id:string;session_token:string;demo_mode:boolean}>('/api/meetings',{method:'POST',body:JSON.stringify(input)});
  setSessionToken(result.meeting_id,result.session_token);return result;
}
export async function uploadMedia(id:string,file:File){const form=new FormData();form.append('file',file);return request<{ok:boolean;segments:number;duration_s:number|null;stt_provider:string;demo_mode:boolean}>(`/api/meetings/${id}/media`,{method:'POST',body:form},id)}
export async function startBot(id:string,url:string){return request<{bot_id:string;state:string;backend:string;label:string}>(`/api/meetings/${id}/bot`,{method:'POST',body:JSON.stringify({meeting_url:url,consent:true})},id)}
export async function finalizeMeeting(id:string){return request<{state:string}>(`/api/meetings/${id}/finalize`,{method:'POST'},id)}
export async function getResult(id:string){return request<{spec:MeetingSpec;segments:Segment[];md:string;provider:string}>(`/api/meetings/${id}/result`,{},id)}
export async function saveResult(id:string,spec:MeetingSpec){return request<{ok:boolean;md:string}>(`/api/meetings/${id}/result`,{method:'PUT',body:JSON.stringify(spec)},id)}
export async function deleteMeeting(id:string){return request<{ok:boolean}>(`/api/meetings/${id}`,{method:'DELETE'},id)}

export type StreamEvent={event:string;data:Record<string,unknown>};
const isRecord=(value:unknown):value is Record<string,unknown>=>typeof value==='object'&&value!==null&&!Array.isArray(value);
export async function consumeSse(response:Response,onEvent:(event:StreamEvent)=>void,signal?:AbortSignal){
  if(!response.ok||!response.body) throw new Error(`Stream failed (${response.status})`);
  const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
  try{
    while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});
      let boundary;while((boundary=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,boundary).replace(/\r/g,'');buffer=buffer.slice(boundary+2);let event='message';const data:string[]=[];
        for(const line of block.split('\n')){if(line.startsWith('event:'))event=line.slice(6).trim();else if(line.startsWith('data:'))data.push(line.slice(5).trimStart())}
        if(data.length){try{const parsed:unknown=JSON.parse(data.join('\n'));onEvent({event,data:isRecord(parsed)?parsed:{}})}catch{onEvent({event,data:{}})}}
      }
    }
    if(buffer.trim()){const match=buffer.match(/(?:^|\n)event:\s*(\w+)/);const data=buffer.match(/(?:^|\n)data:\s*(.*)/);if(data){try{const parsed:unknown=JSON.parse(data[1]);onEvent({event:match?.[1]||'message',data:isRecord(parsed)?parsed:{}})}catch{/* Ignore malformed trailing frames. */}}}
  } finally {if(signal?.aborted) await reader.cancel().catch(()=>undefined)}
}
export async function streamMeeting(id:string,onEvent:(e:StreamEvent)=>void,signal?:AbortSignal){
  const response=await fetch(`${base}/api/meetings/${id}/events`,{headers:{'X-App-Token':appToken(),'X-Session-Token':sessionToken(id)},signal});
  return consumeSse(response,onEvent,signal);
}
export async function streamAsk(id:string,question:string,onEvent:(e:StreamEvent)=>void){
  const response=await fetch(`${base}/api/meetings/${id}/ask`,{method:'POST',headers:{'Content-Type':'application/json','X-App-Token':appToken(),'X-Session-Token':sessionToken(id)},body:JSON.stringify({question})});
  return consumeSse(response,onEvent);
}
