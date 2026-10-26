import {describe,it,expect} from 'vitest';
import {MEET_ONLY_NOTICE,meetUrlError,meetUrlSchema,normalizeMeetUrl} from './meetingUrl';

const bad = [
  'https://zoom.us/j/123456789',
  'https://us02web.zoom.us/j/123456789',
  'https://teams.microsoft.com/l/meetup-join/19%3ameeting',
  'https://teams.live.com/meet/123',
  'http://meet.google.com/abc-defg-hij',
  'meet.google.com/abc-defg-hij',
  'https://meet.google.com.evil.com/abc-defg-hij',
  'https://evilmeet.google.com/abc-defg-hij',
  'https://meet.google.com@evil.com/abc-defg-hij',
  'https://user:pass@meet.google.com/abc-defg-hij',
  'https://meet.google.com:8443/abc-defg-hij',
  'https://meet.google.com/',
  'https://meet.google.com/abc-defg',
  'https://meet.google.com/ABC-DEFG-HIJ',
  'https://meet.google.com/abc-defg-hij/lookup/xyz',
  'https://meet.google.com/abc-defg-hij/../admin',
  'https://meet.google.com/%61bc-defg-hij',
  'https://meet.google.com/abcdefghij',
  'https://meet.google.co/abc-defg-hij',
  'javascript:alert(1)',
  'https://m\u0435et.google.com/abc-defg-hij',
];

describe('Meet-only link rules',()=>{
  it('accepts a Meet link and strips query/fragment',()=>{
    expect(normalizeMeetUrl('https://meet.google.com/abc-defg-hij')).toBe('https://meet.google.com/abc-defg-hij');
    expect(normalizeMeetUrl('https://meet.google.com/xyz-abcd-efg?authuser=0#x')).toBe('https://meet.google.com/xyz-abcd-efg');
  });
  it.each(bad)('rejects %s',url=>{
    expect(normalizeMeetUrl(url)).toBeNull();
    expect(meetUrlSchema.safeParse(url).success).toBe(false);
  });
  it('reports the contract error only for non-empty input',()=>{
    expect(meetUrlError('')).toBeNull();
    expect(meetUrlError('https://zoom.us/j/1')).toBe('Only Google Meet links (meet.google.com) are supported.');
  });
  it('keeps the visible notice wording stable',()=>{
    expect(MEET_ONLY_NOTICE).toContain('Only Google Meet links are supported right now.');
  });
});
