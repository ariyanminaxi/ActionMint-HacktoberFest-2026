import {describe,it,expect,vi,beforeEach,afterEach} from 'vitest';
import {createFrameFlipper,FRAME_FLIP_MS} from './categoryFrames';

describe('A/B category frame flipper',()=>{
  beforeEach(()=>vi.useFakeTimers());
  afterEach(()=>vi.useRealTimers());

  it('starts on frame A and alternates every 130 ms',()=>{
    const seen:string[]=[];
    const flipper=createFrameFlipper();
    flipper.start(frame=>seen.push(frame));
    expect(seen).toEqual(['a']);
    vi.advanceTimersByTime(FRAME_FLIP_MS);
    expect(seen).toEqual(['a','b']);
    vi.advanceTimersByTime(FRAME_FLIP_MS*3);
    expect(seen).toEqual(['a','b','a','b','a']);
    flipper.stop();
  });

  it('stops without further frames and restarts on A',()=>{
    const seen:string[]=[];
    const flipper=createFrameFlipper();
    flipper.start(frame=>seen.push(frame));
    vi.advanceTimersByTime(FRAME_FLIP_MS*2);
    flipper.stop();
    expect(flipper.isRunning()).toBe(false);
    vi.advanceTimersByTime(FRAME_FLIP_MS*10);
    expect(seen).toEqual(['a','b','a']);
    flipper.start(frame=>seen.push(frame));
    expect(seen.at(-1)).toBe('a');
    flipper.stop();
  });

  it('uses 130 ms per flip so reduced motion can opt out of the wiggle',()=>{
    expect(FRAME_FLIP_MS).toBe(130);
  });
});
