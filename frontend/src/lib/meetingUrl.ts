import {z} from 'zod';

/**
 * One Meet-only URL rule for the browser, mirroring `backend/app/meetings/meeting_url.py`
 * (Amendment C.24). Parse with the platform URL parser and compare the parsed host exactly —
 * never `startsWith` or `includes` on the raw string.
 */
export const MEET_HOST = 'meet.google.com';
export const MEET_PLACEHOLDER = 'https://meet.google.com/abc-defg-hij';
export const UNSUPPORTED_MESSAGE = 'Only Google Meet links (meet.google.com) are supported.';
export const MEET_ONLY_NOTICE = 'Only Google Meet links are supported right now. Zoom, Teams and other platforms are not available.';

const MEET_CODE = /^\/[a-z]{3}-[a-z]{4}-[a-z]{3}$/;

export function normalizeMeetUrl(raw: string): string | null {
  if (!raw || !/^[\x20-\x7e]+$/.test(raw)) return null;
  let url: URL;
  try {
    url = new URL(raw.trim());
  } catch {
    return null;
  }
  if (url.protocol !== 'https:') return null;
  if (url.username || url.password) return null;
  if (url.port) return null;
  if (url.hostname !== MEET_HOST) return null;
  if (!MEET_CODE.test(url.pathname)) return null;
  return `https://${MEET_HOST}${url.pathname}`;
}

export function meetUrlError(raw: string): string | null {
  if (!raw.trim()) return null;
  return normalizeMeetUrl(raw) ? null : UNSUPPORTED_MESSAGE;
}

export const meetUrlSchema = z
  .string()
  .refine(value => normalizeMeetUrl(value) !== null, {message: UNSUPPORTED_MESSAGE});
