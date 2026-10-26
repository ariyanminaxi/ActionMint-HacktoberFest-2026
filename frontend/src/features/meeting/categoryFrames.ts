import {CATEGORIES, type CategoryId} from './categories';

/** Decode state of one category frame. `unknown` means "not decoded yet". */
export type FrameState = 'unknown' | 'ready' | 'error';
export type FrameName = 'a' | 'b';
export const FRAME_FLIP_MS = 130;

const states = new Map<string, FrameState>();
const listeners = new Set<() => void>();

export function frameState(src: string): FrameState {
  return states.get(src) ?? 'unknown';
}

export function resetFrameStates() {
  states.clear();
  listeners.forEach(listener => listener());
}

/** Lets the mounted transition re-render as soon as a decode settles. */
export function subscribeFrames(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function settle(src: string, state: FrameState) {
  if (states.get(src) === state) return;
  states.set(src, state);
  listeners.forEach(listener => listener());
}

function ready(src: string) {
  settle(src, 'ready');
}

function failed(src: string) {
  settle(src, 'error');
}

/**
 * Decode every registry frame during idle time (C.23.2). Called once when `/meet/:id`
 * mounts, so the first tab switch already has both frames on hand. A frame that fails
 * stays `error` and the transition falls back to the glyph (A) or stops flipping (B).
 */
export function preloadCategoryFrames(
  scheduleIdle: (run: () => void) => void = defaultIdle,
): void {
  if (typeof Image === 'undefined') return;
  scheduleIdle(() => {
    for (const category of CATEGORIES) {
      for (const src of category.frames) {
        if (states.has(src)) continue;
        states.set(src, 'unknown');
        const image = new Image();
        image.decoding = 'async';
        image.onload = () => {
          if (typeof image.decode === 'function') {
            void image.decode().then(() => ready(src), () => ready(src));
            return;
          }
          ready(src);
        };
        image.onerror = () => failed(src);
        image.src = src;
      }
    }
  });
}

export function defaultIdle(run: () => void): void {
  const idle = (globalThis as {requestIdleCallback?: (cb: () => void, options?: {timeout: number}) => number}).requestIdleCallback;
  if (typeof idle === 'function') idle(run, {timeout: 1200});
  else setTimeout(run, 180);
}

/** True when both frames decoded, so the A/B wiggle is worth showing. */
export function canFlip(category: CategoryId): boolean {
  const entry = CATEGORIES.find(item => item.id === category);
  if (!entry) return false;
  return frameState(entry.frames[0]) === 'ready' && frameState(entry.frames[1]) === 'ready';
}

/** True when frame A is usable (real image) rather than the fallback glyph. */
export function hasFrameA(category: CategoryId): boolean {
  const entry = CATEGORIES.find(item => item.id === category);
  return entry ? frameState(entry.frames[0]) === 'ready' : false;
}

export type Flipper = {
  start(onFrame: (frame: FrameName) => void): Flipper;
  stop(): void;
  isRunning(): boolean;
};

/**
 * Alternates A/B on a fixed clock, starting on A. Kept as a plain factory so tests can
 * drive it with fake timers instead of a browser animation frame.
 */
export function createFrameFlipper(intervalMs: number = FRAME_FLIP_MS): Flipper {
  let timer: ReturnType<typeof setInterval> | null = null;
  let frame: FrameName = 'a';
  const flipper: Flipper = {
    start(onFrame) {
      flipper.stop();
      frame = 'a';
      onFrame(frame);
      timer = setInterval(() => {
        frame = frame === 'a' ? 'b' : 'a';
        onFrame(frame);
      }, intervalMs);
      return flipper;
    },
    stop() {
      if (timer !== null) clearInterval(timer);
      timer = null;
    },
    isRunning() {
      return timer !== null;
    },
  };
  return flipper;
}
