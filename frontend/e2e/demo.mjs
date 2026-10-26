/**
 * ActionMint browser walkthrough — the knowledge.md C.15 three-minute demo.
 *
 * rm -rf docs/screenshots && node e2e/demo.mjs
 *
 * Needs: backend on :8000 (PROVIDER_CHAIN=mock, ENV=dev, APP_TOKEN=<throwaway>) and
 * the Vite dev server on :5173. The token is read from E2E_APP_TOKEN, never stored.
 */
import {chromium} from '@playwright/test';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const BASE = process.env.E2E_BASE ?? 'http://127.0.0.1:5173';
const TOKEN = process.env.E2E_APP_TOKEN ?? '';
const SHOTS = join(process.cwd(), '..', 'docs', 'screenshots');
const failures = [];
const consoleErrors = [];
const badRequests = [];
const notes = {};

const check = (name, ok, detail = '') => {
  if (!ok) failures.push(`${name}${detail ? ` — ${detail}` : ''}`);
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
};

async function shot(page, name) {
  await page.screenshot({path: join(SHOTS, `${name}.png`), fullPage: false});
  console.log(`      shot docs/screenshots/${name}.png`);
}

const browser = await chromium.launch();
const context = await browser.newContext({viewport: {width: 1440, height: 900}, acceptDownloads: true});
const page = await context.newPage();

page.on('console', message => {
  if (message.type() === 'error') consoleErrors.push(message.text().slice(0, 300));
});
page.on('requestfailed', request => {
  const reason = request.failure()?.errorText ?? '';
  if (reason !== 'net::ERR_ABORTED') badRequests.push(`${request.method()} ${request.url()} (${reason})`);
});
page.on('response', response => {
  if (response.status() >= 400) badRequests.push(`${response.request().method()} ${response.url()} -> ${response.status()}`);
});
await page.addInitScript(() => {
  // Deterministic speech synthesis: record calls, never finish on its own so the Stop
  // control stays reachable while the test inspects it.
  window.__speech = {spoken: [], cancel: 0, pause: 0, resume: 0};
  const fakeSynth = {
    speaking: false, paused: false, pending: false,
    getVoices: () => [{name: 'Test Voice', lang: 'en-US', voiceURI: 'test-voice', default: true}],
    addEventListener() {}, removeEventListener() {},
    speak(utterance) { window.__speech.spoken.push({text: utterance.text, rate: utterance.rate}); },
    cancel() { window.__speech.cancel += 1; },
    pause() { window.__speech.pause += 1; },
    resume() { window.__speech.resume += 1; },
  };
  Object.defineProperty(window, 'speechSynthesis', {value: fakeSynth, configurable: true});
  window.SpeechSynthesisUtterance = function (text) { this.text = text; this.rate = 1; this.voice = null; this.onend = null; this.onerror = null; };
});
await page.addInitScript(() => {
  window.__cls = 0;
  window.__long = [];
  new PerformanceObserver(list => { for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
    .observe({type: 'layout-shift', buffered: true});
  new PerformanceObserver(list => { for (const e of list.getEntries()) window.__long.push(Math.round(e.duration)); })
    .observe({type: 'longtask', buffered: true});
});

await mkdir(SHOTS, {recursive: true});

try {
  // 1. Token gate
  await page.goto(BASE, {waitUntil: 'networkidle'});
  check('token gate is shown', await page.getByRole('heading', {name: /enter your demo token/i}).isVisible());
  notes.gateCopy = (await page.locator('.gate-card').innerText()).replace(/\s+/g, ' ').slice(0, 220);
  await shot(page, '01-token-gate-1440');
  await page.fill('#demo-token', TOKEN);
  await page.getByRole('button', {name: /^continue/i}).click();
  await page.waitForSelector('.hero h1', {timeout: 10000});
  check('landing renders after token', await page.locator('.hero h1').isVisible());
  await shot(page, '02-landing-1440');

  // 2. New meeting + demo transcript
  await page.goto(`${BASE}/meet`, {waitUntil: 'networkidle'});
  await page.getByRole('button', {name: /load the 3-minute demo meeting/i}).click();
  const chars = await page.locator('textarea').inputValue();
  check('demo transcript loads', chars.length > 900, `${chars.length} chars`);
  await page.getByRole('button', {name: /build meeting workspace/i}).click();
  await page.waitForURL(/\/meet\/[A-Za-z0-9_-]+$/, {timeout: 15000});

  // 3. Processing view (captured as soon as the route has rendered anything)
  await page.waitForSelector('.processing-wrap, .meeting-tabs', {timeout: 20000});
  await shot(page, '03-processing');
  notes.processingText = (await page.locator('.processing-wrap').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 200);

  // 4. Results
  await page.waitForSelector('.meeting-tabs', {timeout: 30000});
  const reviewUrl = page.url();
  const tabs = await page.locator('.meeting-tab').allInnerTexts();
  check('review tabs render', tabs.length >= 8, tabs.join(' | '));
  const tldr = (await page.locator('.summary-tldr').innerText()).trim();
  check('summary is filled', tldr.length > 30, `${tldr.length} chars`);
  await page.waitForTimeout(900); // let the staggered reveal finish before the screenshot
  await shot(page, '04-review-overview-1440');

  // 5. Category transition on a real tab switch
  // Let the on-load reveal animation finish, otherwise the tab bar is still settling.
  await page.waitForTimeout(900);
  const before = await page.locator('.meeting-content').innerText();
  const tabsBefore = await page.locator('.meeting-tabs').boundingBox();
  await page.getByRole('tab', {name: /^Actions/i}).click();
  await page.waitForTimeout(120);
  const overlaysMid = await page.locator('.category-transition').count();
  const framesMid = await page.locator('.category-transition .category-frame').count();
  await shot(page, '05-tab-transition');
  const after = await page.locator('.meeting-content').innerText();
  const visibleFrames = await page.locator('.category-transition .category-frame')
    .evaluateAll(nodes => nodes.filter(node => getComputedStyle(node).visibility === 'visible').length);
  const overlayBlocks = await page.locator('.category-transition')
    .evaluate(node => getComputedStyle(node).pointerEvents !== 'none');
  const tabsDuring = await page.locator('.meeting-tabs').boundingBox();
  check('content changes immediately on tab switch', before !== after);
  check('transition overlay appears', overlaysMid === 1, `${overlaysMid} overlay(s)`);
  check('real A/B frames are used', framesMid === 2, `${framesMid} <img> frame(s)`);
  check('only one frame is visible at a time', visibleFrames === 1, `${visibleFrames} visible`);
  check('transition never blocks clicks', overlayBlocks === false);
  check('tab bar does not shift during the transition', tabsBefore !== null && tabsDuring !== null
    && Math.abs(tabsBefore.y - tabsDuring.y) < 1, `${tabsBefore?.y} -> ${tabsDuring?.y}`);
  await page.waitForTimeout(1100);
  check('overlay removes itself', (await page.locator('.category-transition').count()) === 0);
  await shot(page, '06-actions-tab');

  // 6. Edit owner + due date, then undo
  const firstAction = page.locator('.action-editor').first();
  const ownerInput = firstAction.locator('.action-fields label').first().locator('input');
  const dueInput = firstAction.locator('.action-fields label').nth(1).locator('input');
  notes.ownerBefore = await ownerInput.inputValue();
  notes.dueBefore = await dueInput.inputValue();
  await ownerInput.fill('Anita Rao');
  await dueInput.fill('2026-11-02');
  await page.waitForTimeout(250);
  check('owner edit sticks', (await ownerInput.inputValue()) === 'Anita Rao');
  check('due edit sticks', (await dueInput.inputValue()) === '2026-11-02');
  await page.getByRole('button', {name: /^Undo/i}).click();
  await page.waitForTimeout(200);
  check('first undo reverts the last edit (due date)', (await dueInput.inputValue()) === notes.dueBefore,
    `due "${notes.dueBefore}" -> "${await dueInput.inputValue()}"`);
  await page.getByRole('button', {name: /^Undo/i}).click();
  await page.waitForTimeout(200);
  notes.ownerAfterUndo = await ownerInput.inputValue();
  check('second undo restores the owner', notes.ownerAfterUndo === notes.ownerBefore, `"${notes.ownerBefore}" -> "${notes.ownerAfterUndo}"`);
  await ownerInput.fill('Anita Rao');
  await page.waitForTimeout(900); // let the debounced PUT settle

  // 6b. Owner lanes, add, reorder, merge, and export-blocking validation
  await page.getByRole('button', {name: /^Add item/i}).click();
  await page.waitForTimeout(150);
  const laneNames = await page.locator('.lane-head h3').allInnerTexts();
  check('actions are grouped by owner', laneNames.some(name => name.startsWith('Anita')) && laneNames.includes('Unassigned'), laneNames.join(' | '));
  check('unassigned lane is present and amber', await page.locator('.owner-lane.unassigned').isVisible());

  const tasksBefore = await page.locator('.action-editor .task-input').evaluateAll(nodes => nodes.map(node => node.value));
  await page.locator('.action-editor').first().getByRole('button', {name: 'Move action down'}).click();
  await page.waitForTimeout(150);
  const tasksMoved = await page.locator('.action-editor .task-input').evaluateAll(nodes => nodes.map(node => node.value));
  check('reorder moves the item down', tasksMoved[0] === tasksBefore[1] && tasksMoved[1] === tasksBefore[0]);
  await page.getByRole('button', {name: /^Undo/i}).click();
  await page.waitForTimeout(150);
  const tasksRestored = await page.locator('.action-editor .task-input').evaluateAll(nodes => nodes.map(node => node.value));
  check('undo restores the order', JSON.stringify(tasksRestored) === JSON.stringify(tasksBefore));

  const countBeforeMerge = await page.locator('.action-editor').count();
  await page.locator('.action-editor').nth(1).getByRole('button', {name: /merge into previous/i}).click();
  await page.waitForTimeout(150);
  check('merge folds one action into the one above', (await page.locator('.action-editor').count()) === countBeforeMerge - 1);
  await page.getByRole('button', {name: /^Undo/i}).click();
  await page.waitForTimeout(150);
  // Drop the item added for the lane test so the export stays the golden three.
  const lastAction = page.locator('.action-editor').last();
  await lastAction.getByRole('button', {name: 'Delete action'}).click();
  await page.waitForTimeout(150);
  check('delete removes the added item', (await page.locator('.action-editor').count()) === 3);

  const taskInput = page.locator('.action-editor .task-input').first();
  const originalTask = await taskInput.inputValue();
  await taskInput.fill('');
  await page.waitForTimeout(200);
  check('validation banner appears for an empty task', await page.locator('.validation-banner').isVisible());
  check('export is blocked while invalid', await page.getByRole('button', {name: /export notes/i}).isDisabled());
  await taskInput.fill(originalTask);
  await page.waitForTimeout(250);
  check('validation clears after the fix', (await page.locator('.validation-banner').count()) === 0
    && await page.getByRole('button', {name: /export notes/i}).isEnabled());

  // 6c. Listen (text to speech)
  const listen = page.locator('.listen-bar');
  check('Listen bar appears in the review layout', await listen.isVisible());
  await listen.getByRole('button', {name: /play read-out/i}).click();
  await page.waitForTimeout(150);
  const spoken = await page.evaluate(() => window.__speech.spoken);
  check('Play starts the read-out with the summary', spoken.length >= 1 && /launch/i.test(spoken[0].text), JSON.stringify(spoken[0]));
  check('Stop is offered while reading', await listen.getByRole('button', {name: /^Stop/i}).isVisible());
  await listen.getByRole('button', {name: /options/i}).click();
  check('section checkboxes, speed and voice are available', await page.locator('#listen-options').isVisible()
    && await page.locator('#listen-options select').count() === 2);
  await shot(page, '16-listen-bar');
  await listen.getByRole('button', {name: /^Stop/i}).click();
  await page.waitForTimeout(100);
  check('Stop cancels speech', (await page.evaluate(() => window.__speech.cancel)) >= 1);
  await listen.getByRole('button', {name: /options/i}).click();

  // 7. Exports
  const mdDownload = page.waitForEvent('download', {timeout: 10000});
  await page.getByRole('button', {name: /export notes/i}).click();
  const md = await mdDownload;
  check('markdown exports', /\.md$/.test(md.suggestedFilename()), md.suggestedFilename());
  await md.saveAs(join(SHOTS, '..', '..', '_scratch', 'export.md')).catch(() => {});

  await page.locator('.export-menu').hover();
  const icsItem = page.locator('.export-dropdown button', {hasText: 'ICS'});
  await icsItem.waitFor({state: 'visible', timeout: 5000});
  // Register the listener BEFORE the click: a download that fires on click is otherwise missed.
  const icsDownload = page.waitForEvent('download', {timeout: 10000});
  await icsItem.click();
  const ics = await icsDownload;
  check('ics exports', /\.ics$/.test(ics.suggestedFilename()), ics.suggestedFilename());
  check('md export carries the edited owner', (await readFile(join(SHOTS, '..', '..', '_scratch', 'export.md'), 'utf8')).includes('Anita Rao'));
  check('ics export contains a VEVENT', (await readFile(await ics.path(), 'utf8')).includes('BEGIN:VEVENT'));

  // 8. Simulated bot with consent + Meet-only notice
  await page.goto(`${BASE}/meet`, {waitUntil: 'networkidle'});
  await page.getByRole('tab', {name: /meeting link/i}).click();
  const notice = (await page.locator('.platform-notice').innerText()).replace(/\s+/g, ' ');
  check('Meet-only notice is visible', /Only Google Meet links/.test(notice), notice.slice(0, 90));
  await page.locator('input[type=url]').fill('https://zoom.us/j/123');
  await page.waitForTimeout(120);
  check('non-Meet link shows an inline error', await page.locator('.field-error').isVisible());
  const startButton = page.getByRole('button', {name: /start simulated capture/i});
  check('start is blocked for a non-Meet link', await startButton.isDisabled());
  await shot(page, '07-meet-only-error');
  await page.locator('input[type=url]').fill('https://meet.google.com/abc-defg-hij');
  await page.locator('.checkbox-line input').check();
  check('start enabled for a valid Meet link', await startButton.isEnabled());
  await startButton.click();
  await page.waitForURL(/\/meet\/[A-Za-z0-9_-]+$/, {timeout: 15000});
  await page.waitForSelector('.meeting-tabs', {timeout: 40000});
  check('simulated bot reaches review', await page.locator('.meeting-tabs').isVisible());
  await shot(page, '08-simulated-bot-review');

  // 9. Responsive passes on the review screen
  for (const [width, name] of [[360, '09-review-360'], [768, '10-review-768']]) {
    await page.setViewportSize({width, height: 800});
    await page.waitForTimeout(350);
    await page.screenshot({path: join(SHOTS, `${name}.png`), fullPage: true});
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    check(`no horizontal overflow at ${width}px`, overflow <= 1, `${overflow}px`);
  }
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(BASE, {waitUntil: 'networkidle'});
  await page.waitForTimeout(400);
  await shot(page, '11-landing-1440-final');

  // 10. Landing + new-meeting at the two other breakpoints (full page)
  for (const [width, name] of [[360, '12-landing-360'], [768, '13-landing-768']]) {
    await page.setViewportSize({width, height: 800});
    await page.waitForTimeout(350);
    await page.screenshot({path: join(SHOTS, `${name}.png`), fullPage: true});
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    check(`landing has no horizontal overflow at ${width}px`, overflow <= 1, `${overflow}px`);
  }
  await page.setViewportSize({width: 360, height: 800});
  await page.goto(`${BASE}/meet`, {waitUntil: 'networkidle'});
  await page.waitForTimeout(300);
  await page.screenshot({path: join(SHOTS, '14-new-meeting-360.png'), fullPage: true});
  const meetOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check('new meeting has no horizontal overflow at 360px', meetOverflow <= 1, `${meetOverflow}px`);
  await page.setViewportSize({width: 768, height: 800});
  await page.waitForTimeout(200);
  await page.screenshot({path: join(SHOTS, '15-new-meeting-768.png'), fullPage: true});
  await page.setViewportSize({width: 1440, height: 900});

  // 11. Keyboard: focus ring + arrow-key tab navigation
  await page.goto(BASE, {waitUntil: 'networkidle'});
  await page.keyboard.press('Tab');
  const focusRing = await page.evaluate(() => {
    const el = document.activeElement;
    if (!el) return null;
    const style = getComputedStyle(el);
    return {tag: el.tagName, outline: style.outlineStyle, width: style.outlineWidth, boxShadow: style.boxShadow};
  });
  check('first Tab stop exposes a visible focus ring', focusRing !== null
    && (focusRing.outline !== 'none' || focusRing.boxShadow !== 'none'), JSON.stringify(focusRing));

  // 12. Motion measurements: transition frames, reduced motion, Low effects
  const motionDir = join(SHOTS, '..', '..', '_scratch', 'motion');
  await mkdir(motionDir, {recursive: true});
  await page.emulateMedia({reducedMotion: 'no-preference'});
  await page.goto(reviewUrl, {waitUntil: 'networkidle'});
  await page.waitForSelector('.meeting-tabs', {timeout: 30000});
  await page.waitForTimeout(900);
  await page.screenshot({path: join(motionDir, 'frame-000.png')});
  await page.getByRole('tab', {name: /^Decisions/i}).click();
  await page.waitForTimeout(150);
  await page.screenshot({path: join(motionDir, 'frame-150.png')});
  await page.waitForTimeout(300);
  await page.screenshot({path: join(motionDir, 'frame-450.png')});
  notes.clsReview = await page.evaluate(() => Math.round(window.__cls * 10000) / 10000);

  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.goto(reviewUrl, {waitUntil: 'networkidle'});
  await page.waitForSelector('.meeting-tabs', {timeout: 30000});
  await page.waitForTimeout(500);
  await page.getByRole('tab', {name: /^Actions/i}).click();
  await page.waitForTimeout(60);
  const reducedOverlay = await page.locator('.category-transition').count();
  const reducedDurations = await page.evaluate(() => document.getAnimations()
    .filter(animation => animation.playState === 'running')
    .map(animation => Math.round(Number(animation.effect?.getTiming().duration) || 0)));
  notes.reducedDurations = reducedDurations;
  check('reduced motion uses a short fade instead of the fly-through', reducedOverlay === 1
    && reducedDurations.length > 0 && Math.max(...reducedDurations) <= 400, JSON.stringify(reducedDurations));
  await page.waitForTimeout(500);
  check('reduced transition removes itself', (await page.locator('.category-transition').count()) === 0);
  // Measured, not asserted near-zero: the review route mount shifts ~0.05 on a cold load (lazy
  // chunk + processing -> review swap). That is inside the web-vitals "good" budget (< 0.1) but
  // it is NOT zero, and FINAL_REPORT.md says so.
  check('review route CLS stays in the good band (< 0.1)', notes.clsReview <= 0.1, String(notes.clsReview));

  await page.emulateMedia({reducedMotion: 'no-preference'});
  await page.getByRole('button', {name: 'Settings'}).click();
  await page.getByRole('button', {name: 'Low effects'}).click();
  check('Low effects is applied to the document', await page.evaluate(() => document.documentElement.dataset.lowEffects === 'true'));
  await page.locator('.panel-close').click();
  await page.goto(reviewUrl, {waitUntil: 'networkidle'});
  await page.waitForSelector('.meeting-tabs', {timeout: 30000});
  await page.waitForTimeout(400);
  const lowEffectDurations = await page.evaluate(() => document.getAnimations()
    .filter(animation => animation.playState === 'running')
    .map(animation => Math.round(Number(animation.effect?.getTiming().duration) || 0)));
  notes.lowEffectDurations = lowEffectDurations;
  check('Low effects leaves no long reveal animations', lowEffectDurations.every(duration => duration <= 400), JSON.stringify(lowEffectDurations));
  await page.screenshot({path: join(SHOTS, '17-low-effects.png')});

  check('no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' | '));
  check('no failed or 4xx requests', [...new Set(badRequests)].length === 0, [...new Set(badRequests)].slice(0, 3).join(' | '));
  notes.cls = await page.evaluate(() => Math.round(window.__cls * 10000) / 10000);
  notes.longTasks = await page.evaluate(() => window.__long);
} catch (error) {
  failures.push(`script error: ${error.message}`);
  await shot(page, '99-failure').catch(() => {});
} finally {
  notes.consoleErrors = consoleErrors;
  notes.badRequests = [...new Set(badRequests)];
  const report = {failures, notes};
  await writeFile(join(process.cwd(), '..', '_scratch', 'e2e-report.json'), JSON.stringify(report, null, 2));
  console.log('\n--- console errors ---');
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(none)');
  console.log('--- failed/4xx requests ---');
  console.log(notes.badRequests.length ? notes.badRequests.join('\n') : '(none)');
  console.log(`--- CLS ${notes.cls ?? 'n/a'} | long tasks ${JSON.stringify(notes.longTasks ?? [])} ---`);
  console.log(`\n${failures.length ? `${failures.length} FAILURE(S)` : 'ALL CHECKS PASSED'}`);
  await browser.close();
  process.exit(failures.length ? 1 : 0);
}
