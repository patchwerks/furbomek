import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const skill = process.env.OMO_BROWSER_SKILL;
const url = process.env.STUDIO_URL;
const evidence = process.env.STUDIO_EVIDENCE_DIR;
if (!skill || !url || !evidence) throw new Error('Set OMO_BROWSER_SKILL, STUDIO_URL and STUDIO_EVIDENCE_DIR');
const { loadOmowright } = await import(pathToFileURL(join(skill,'scripts/omowright.mjs')).href);
const { omowright } = await loadOmowright();
const profile = await mkdtemp(join(tmpdir(),'studio-browser-'));
const browser = await omowright.connectPipe({ browserPath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', browserArgs:['--headless','--no-first-run',`--user-data-dir=${profile}`], storageRoot:profile });
const results = [];
const captures = [];
await mkdir(evidence,{recursive:true});
let page;
try {
  page = await browser.newTab('about:blank');
  const sid = await page.resolveSessionId();
  async function snapshot() { return omowright.compactSnapshot(await page.snapshot()); }
  async function ref(kind, label) {
    const tree = await snapshot();
    const line = tree.split('\n').find(line=>line.includes(`${kind} "${label}"`));
    const match = line?.match(/\[ref=(\w+)\]/);
    assert.ok(match, `Missing ${kind} ${label}\n${tree}`); return match[1];
  }
  async function click(label) { console.log('CLICK',label); await page.locator(await ref('button',label)).click(); }
  async function select(label,value) { await page.locator(await ref('combobox',label)).selectOption(value); }
  async function fill(label,value) { await page.locator(await ref('textbox',label)).fill(value); }
  async function until(text) {
    await page.evaluate(text => new Promise((resolve,reject)=> {
      const check = () => document.body.innerText.includes(text);
      if (check()) { resolve(true); return; }
      const timeout=setTimeout(()=>{ observer.disconnect(); reject(new Error(`Missing UI text: ${text}`)); },20000);
      const observer=new MutationObserver(()=>{if(check()){clearTimeout(timeout);observer.disconnect();resolve(true);}});
      observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true});
    }),text);
  }
  async function shot(name) { const file=join(evidence,`${name}.png`); await writeFile(file,await page.screenshot()); captures.push(file); return file; }
  async function applied() { return page.evaluate(async()=>{const r=await fetch('/fixture/state');return r.json();}); }
  async function captureRoute(route, device, theme) {
    const size = device === 'iphone-14' ? {width:390,height:844,deviceScaleFactor:3,mobile:true,hasTouch:true} : {width:device === 'desktop-1920' ? 1920 : 1440,height:device === 'desktop-1920' ? 1080 : 900,deviceScaleFactor:1,mobile:false,hasTouch:false};
    await page.setViewportSize({width:size.width,height:size.height});
    await omowright.emulate(page,size);
    await page.cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme},{name:'prefers-reduced-motion',value:'reduce'}]},sid);
    await page.goto(url); await until('Fixture connected');
    await page.cdp.send('Emulation.setDeviceMetricsOverride',{width:size.width,height:size.height,deviceScaleFactor:size.deviceScaleFactor,mobile:size.mobile,screenWidth:size.width,screenHeight:size.height},sid);
    if (route !== 'Effects') await click(route);
    await page.evaluate(()=>document.fonts.ready);
    await page.evaluate(()=>window.scrollTo(0,0));
    const top=await shot(`${route}-${device}-${theme}-top`);
    const metrics=await page.evaluate(()=>({width:innerWidth,dpr:devicePixelRatio,touch:navigator.maxTouchPoints,scroll:document.documentElement.scrollWidth,controls:[...document.querySelectorAll('button,input,select,summary')].filter(e=>e.getBoundingClientRect().width>0).map(e=>({name:e.getAttribute('aria-label')||e.textContent?.trim().slice(0,50)||e.tagName,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))}));
    assert.equal(metrics.width,size.width); assert.equal(metrics.dpr,size.deviceScaleFactor); if(size.mobile) assert.ok(metrics.touch>0);
    assert.ok(metrics.scroll<=metrics.width,`Horizontal overflow ${route}/${device}`);
    for(const c of metrics.controls) assert.ok(c.width>=24 && c.height>=24,`Small target ${JSON.stringify(c)}`);
    await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const scroll = await page.evaluate(()=>({y:scrollY,height:innerHeight,total:document.documentElement.scrollHeight}));
    assert.ok(scroll.y+scroll.height>=scroll.total-2, `End of page not visible: ${JSON.stringify(scroll)}`);
    const end=await shot(`${route}-${device}-${theme}-end`);
    results.push({scenario:`${route}/${device}/${theme} reflow and targets`,passed:true,top,end,metrics,scroll});
  }
  await omowright.emulate(page,'desktop-1440');
  await page.goto(url); await until('Fixture connected');
  await select('Look','rgb'); await fill('Intensity · 0–100%','37'); await click('Preview'); await until('Validated fixture preview');
  assert.ok((await snapshot()).includes('Synthetic fixed RGB preview') || (await page.evaluate(()=>document.querySelector('.rgb-fixture') !== null)));
  await page.locator(await ref('button','Apply to fixture')).hover(); await shot('happy-preview-hover');
  await click('Apply to fixture'); await until('Applied to fixture only.');
  assert.equal((await applied()).applied.intensity_percent,37);
  await click('Save preset'); await until('Preset saved locally.');
  await fill('Intensity · 0–100%','65'); await click('Preview'); await until('Validated fixture preview'); await click('Apply to fixture'); await until('Applied to fixture only.');
  await click('Revert applied'); await until('Reverted to the previous'); assert.equal((await applied()).applied.intensity_percent,37);
  await fill('Intensity · 0–100%','72'); await click('Preview'); await until('Validated fixture preview'); await click('Apply to fixture'); await until('Applied to fixture only.');
  await click('Restore saved'); await until('Saved preset restored explicitly.'); assert.equal((await applied()).applied.intensity_percent,37);
  await shot('happy-restored'); results.push({scenario:'browser preview apply save revert and explicit restore',passed:true,state:await applied()});
  await fill('Intensity · 0–100%','101'); await click('Preview'); await until('Invalid effect'); await shot('failure-range');
  await select('Effect capability','motion.qualified.v1');
  assert.match(await snapshot(),/button "Preview".*\[disabled\]/); await shot('failure-blocked');
  await select('Effect capability','graphics.pulse.v1'); await fill('Intensity · 0–100%','42');
  await page.locator(await ref('generic','Fixture failure scenarios')).click();
  await click('Simulate stale state'); await until('Stale state');
  assert.match(await snapshot(),/button "Preview".*\[disabled\]/); await shot('failure-stale');
  await click('Reconnect'); await until('Reconnected.');
  assert.equal(await page.evaluate(()=>document.querySelector('input[type=number]')?.value),'42');
  await click('Simulate disconnect'); await until('Disconnected'); await shot('failure-disconnected');
  await click('Reconnect'); await until('Reconnected.');
  assert.equal(await page.evaluate(()=>document.querySelector('input[type=number]')?.value),'42');
  results.push({scenario:'invalid range, blocked motion, stale state and disconnect block writes; dirty draft survives reconnect',passed:true});
  await click('Reactions');
  await click('Validate dry-run'); await until('Dry-run timeline'); assert.match(await snapshot(),/Skipped.*Unavailable/); await shot('happy-reaction');
  await click('Cancel rehearsal'); await until('Fixture rehearsal cancelled'); assert.equal((await applied()).run,'cancelled');
  await page.locator('input[type="number"]').fill('1'); await click('Validate dry-run'); await until('Cue graph rejected'); await shot('failure-graph');
  await click('Framing'); await click('Add fallback rule');
  await page.locator(await ref('button','Move rule 3 up')).click();
  assert.equal(await page.evaluate(()=>document.querySelector('#rule-1')?.value),'hold');
  await shot('happy-framing-order');
  results.push({scenario:'liquidation dry-run skips motion; cancellation, canonical rejection and framing ordering work',passed:true});
  for(const route of ['Effects','Reactions','Framing']) for(const device of ['iphone-14','desktop-1440','desktop-1920']) for(const theme of ['light','dark']) await captureRoute(route,device,theme);
  await page.setViewportSize({width:320,height:800});
  await omowright.emulate(page,{width:320,height:800,deviceScaleFactor:1,mobile:true,hasTouch:true});
  await page.goto(url); await until('Fixture connected');
  assert.equal(await page.evaluate(()=>innerWidth),320);
  await page.evaluate(()=>{document.documentElement.style.setProperty('letter-spacing','.12em');document.documentElement.style.setProperty('word-spacing','.16em');document.querySelectorAll('p').forEach(e=>e.style.marginBottom='2em');});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await shot('reflow-320-text-spacing');
  await page.locator(await ref('generic','Capability inventory')).click();
  await select('Category','hardware');
  await click('Raw depth and IR export unsupported · capture');
  await until('No exported raw image artifact');
  await select('Effect capability','sfx.preset.v1'); await click('Preview'); await until('Validated fixture preview'); await click('Apply to fixture'); await until('Applied to fixture only.');
  assert.equal((await applied()).applied.capability,'sfx.preset.v1');
  await click('Restore saved'); await until('Saved preset restored explicitly.');
  await shot('happy-mobile-selection');
  results.push({scenario:'320px mobile inventory selection, synthetic sound preview/apply and saved restore',passed:true});
  await page.setViewportSize({width:1440,height:900}); await omowright.emulate(page,'desktop-1440'); await page.goto(url); await until('Fixture connected');
  await page.keyboard.press('Tab'); await shot('keyboard-focus');
  await page.goto(new URL('/',url).href); await until('Live API unavailable');
  assert.equal(await page.evaluate(()=>document.querySelector('nav')===null),true); await shot('live-unavailable');
  await writeFile(join(evidence,'browser.json'),JSON.stringify({passed:true,engine:'OMO owned Chrome over pipe',results,captures},null,2));
  console.log(JSON.stringify({passed:true,scenarios:results.length,captures:captures.length}));
} catch(error) { if(page){await writeFile(join(evidence,'browser-failure-snapshot.txt'),omowright.compactSnapshot(await page.snapshot())); await writeFile(join(evidence,'browser-failure.png'),await page.screenshot());} throw error; } finally { await browser.close(); await rm(profile,{recursive:true,force:true}); await writeFile(join(evidence,'browser-cleanup.json'),JSON.stringify({browserClosed:true,profileRemoved:true})); }
