import {describe,it,expect} from 'vitest';
import {consumeSse} from './client';

describe('SSE parser',()=>{
  it('reassembles event frames split across arbitrary chunks',async()=>{
    const chunks=['event: sta','tus\ndata: {"state":"extracting"}\n\neve','nt: token\ndata: {"text":"hi"}\n\n'];
    const stream=new ReadableStream<Uint8Array>({start(controller){for(const x of chunks)controller.enqueue(new TextEncoder().encode(x));controller.close()}});
    const events:{event:string;data:Record<string,unknown>}[]=[];
    await consumeSse(new Response(stream),e=>events.push(e));
    expect(events).toEqual([{event:'status',data:{state:'extracting'}},{event:'token',data:{text:'hi'}}]);
  });
});
