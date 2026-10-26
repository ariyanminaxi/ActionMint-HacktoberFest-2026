import {lazy,Suspense,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {BrowserRouter,Routes,Route,Link,useLocation} from 'react-router-dom';
import {ArrowUpRight,Command,Settings2,ShieldCheck,SunMoon} from 'lucide-react';
import {gsap} from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
import Lenis from 'lenis';
// Routes are split so the landing page does not pay for the review workspace or GSAP-heavy tabs.
const HomePage=lazy(()=>import('./pages/HomePage'));
const NewMeetingPage=lazy(()=>import('./pages/NewMeetingPage'));
const MeetingPage=lazy(()=>import('./pages/MeetingPage'));
import {getAppToken,setAppToken,getHealth} from './api/client';
import {useSettingsStore} from './store/useSettingsStore';
import {useMeetingStore} from './store/useMeetingStore';

gsap.registerPlugin(ScrollTrigger);

function BrandMark({home=false,mini=false}:{home?:boolean;mini?:boolean}){
 return <span className={`brand-mark${mini?' mini':''}${home?' home-logo-float':''}`}><img src="/assets/actionmint-mark.png" alt="" draggable={false}/></span>;
}
function TokenGate({onSave}:{onSave:(v:string)=>void}){
 const[value,setValue]=useState('');const[error,setError]=useState('');
 return <div className="gate-backdrop"><section className="gate-card"><div className="gate-emblem"><img src="/assets/actionmint-mark.png" alt=""/></div><p className="eyebrow">PRIVATE WORKSPACE</p><h2>Enter your demo token</h2><p className="muted">The project uses a shared app token for evaluator access. It stays in this browser tab only.</p><form onSubmit={e=>{e.preventDefault();if(!value.trim()){setError('Paste the token from the submission details.');return}onSave(value.trim())}}><label htmlFor="demo-token">Workspace token</label><input id="demo-token" autoComplete="off" value={value} onChange={e=>setValue(e.target.value)} placeholder="Paste token"/><div className="token-error">{error}</div><button className="button primary full" type="submit">Continue <ArrowUpRight size={16}/></button></form><button className="quiet-button demo-token-button" onClick={()=>onSave('dev-token-change-me')}>Use local demo token</button></section></div>;
}
function Header(){
 const location=useLocation();const{theme,setTheme,lowEffects,setLowEffects,categoryAnimations,setCategoryAnimations}=useSettingsStore();
 const[health,setHealth]=useState<'checking'|'online'|'offline'>('checking');const[settingsOpen,setSettingsOpen]=useState(false);const reset=useMeetingStore(s=>s.reset);
 useEffect(()=>{let active=true;const check=async()=>{try{const h=await getHealth();if(active)setHealth(h.providers.some(p=>p.ok)?'online':'offline')}catch{if(active)setHealth('offline')}};void check();const timer=window.setInterval(check,15000);return()=>{active=false;clearInterval(timer)}},[]);
 return <><header className="topbar"><Link to="/" className="brand" aria-label="ActionMint home"><BrandMark home={location.pathname==='/'}/><span>ActionMint</span></Link><nav className="topnav"><Link className={location.pathname.startsWith('/meet')?'nav-link active':'nav-link'} to="/meet">Workspace</Link><a className="nav-link" href="/#how">How it works</a></nav><div className="top-actions"><span className={`health-pill ${health}`}><i/>{health==='online'?'System ready':health==='offline'?'Demo available':'Checking'}</span><button className="icon-button" aria-label="Settings" onClick={()=>setSettingsOpen(true)}><Settings2 size={18}/></button><Link to="/meet" className="button small-button">New meeting <span>↗</span></Link></div></header>{settingsOpen&&<div className="settings-scrim" onMouseDown={e=>{if(e.target===e.currentTarget)setSettingsOpen(false)}}><aside className="settings-panel"><button className="panel-close" onClick={()=>setSettingsOpen(false)}>×</button><p className="eyebrow">PREFERENCES</p><h2>Workspace settings</h2><div className="setting-row"><div><strong>Theme</strong><small>Warm cream or deep, colorful night.</small></div><button className="outline-button" onClick={()=>setTheme(theme==='dark'?'light':'dark')}><SunMoon size={16}/>{theme==='dark'?'Dark':'Light'}</button></div><div className="setting-row"><div><strong>Low effects</strong><small>Reduce motion and ambient effects.</small></div><button className={`toggle ${lowEffects?'on':''}`} aria-label="Low effects" aria-pressed={lowEffects} onClick={()=>setLowEffects(!lowEffects)}><span/></button></div><div className="setting-row category-setting"><div><strong>Category animations</strong><small>Choose how result tabs transition.</small></div><div className="category-mode-options" role="group" aria-label="Category animations">{(['on','reduced','off'] as const).map(mode=><button key={mode} className={`outline-button${categoryAnimations===mode?' selected':''}`} aria-pressed={categoryAnimations===mode} onClick={()=>setCategoryAnimations(mode)}>{mode==='on'?'On':mode==='reduced'?'Reduced':'Off'}</button>)}</div></div><div className="privacy-box"><ShieldCheck size={18}/><p><strong>Private by default</strong><br/>Transcripts live in temporary server memory and are purged after the session expires. Cloud history is optional and off unless configured.</p></div><div className="setting-row"><div><strong>App token</strong><small>Stored in sessionStorage for this tab.</small></div><button className="outline-button" onClick={()=>{sessionStorage.removeItem('actionmint.appToken');sessionStorage.removeItem('morrow.appToken');setSettingsOpen(false);window.location.reload()}}>Change</button></div><button className="quiet-button" onClick={()=>{reset();setSettingsOpen(false)}}><Command size={15}/> Reset current meeting view</button><p className="settings-version">ActionMint · Build 1.0 · <a href="https://github.com" target="_blank" rel="noreferrer">Open project <ArrowUpRight size={12}/></a></p></aside></div>}</>;
}
function NotFound(){return <main className="notfound"><p className="eyebrow">404 / OFF THE RECORD</p><h1>This page wasn't in the minutes.</h1><Link to="/" className="button primary">Back to home <ArrowUpRight size={16}/></Link></main>}
function AppInner(){
 const[token,setToken]=useState(getAppToken());const{theme,lowEffects}=useSettingsStore();const location=useLocation();const frame=useRef<HTMLDivElement|null>(null);
 const[systemReduced,setSystemReduced]=useState(()=>typeof window!=='undefined'&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
 useEffect(()=>{const media=window.matchMedia('(prefers-reduced-motion: reduce)');const update=()=>setSystemReduced(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
 useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lowEffects=String(lowEffects);document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='light'?'#f4efe4':'#11151d')},[theme,lowEffects]);
 useLayoutEffect(()=>{
  if(lowEffects||systemReduced)return;
  const lenis=new Lenis({smoothWheel:true,lerp:.085});
  const tick=(time:number)=>lenis.raf(time*1000);
  const visibility=()=>{if(document.visibilityState==='hidden')lenis.stop();else lenis.start()};
  lenis.on('scroll',ScrollTrigger.update);gsap.ticker.add(tick);gsap.ticker.lagSmoothing(0);document.addEventListener('visibilitychange',visibility);
  return()=>{document.removeEventListener('visibilitychange',visibility);gsap.ticker.remove(tick);lenis.destroy()};
 },[lowEffects,systemReduced]);
 useLayoutEffect(()=>{
  const root=frame.current;if(!root)return;
  if(lowEffects||systemReduced){ScrollTrigger.getAll().forEach(trigger=>trigger.kill());return}
  const ctx=gsap.context(()=>{},root);let order=0;
  const animate=(element:HTMLElement)=>{
    if(element.dataset.revealBound==='true')return;
    element.dataset.revealBound='true';const delay=Math.min(order++*.035,.18);
    ctx.add(()=>gsap.fromTo(element,{autoAlpha:0,y:30,rotateX:2,transformPerspective:1000},{autoAlpha:1,y:0,rotateX:0,duration:.78,delay,ease:'power3.out',scrollTrigger:{trigger:element,start:'top 88%',once:true}}));
  };
  root.querySelectorAll<HTMLElement>('[data-reveal]').forEach(animate);
  const observer=new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes){if(!(node instanceof HTMLElement))continue;if(node.matches('[data-reveal]'))animate(node);node.querySelectorAll<HTMLElement>('[data-reveal]').forEach(animate)}});
  observer.observe(root,{childList:true,subtree:true});
  let alive=true;const refresh=()=>{if(alive)ScrollTrigger.refresh()};
  void document.fonts?.ready.then(refresh);const imagePromises=Array.from(root.querySelectorAll('img')).map(img=>typeof img.decode==='function'?img.decode().catch(()=>undefined):Promise.resolve());void Promise.all(imagePromises).then(refresh);
  const resize=()=>ScrollTrigger.refresh();window.addEventListener('resize',resize,{passive:true});requestAnimationFrame(refresh);
  return()=>{alive=false;observer.disconnect();window.removeEventListener('resize',resize);ctx.revert();root.querySelectorAll<HTMLElement>('[data-reveal-bound="true"]').forEach(element=>delete element.dataset.revealBound)};
 },[location.pathname,lowEffects,systemReduced]);
 useEffect(()=>{
  if(lowEffects||systemReduced||window.matchMedia('(pointer: coarse)').matches)return;
  const cards=Array.from(document.querySelectorAll<HTMLElement>('[data-tilt]'));
  const cleanups=cards.map(card=>{
   let frameId=0;let px=0;let py=0;
   const move=(event:PointerEvent)=>{if(event.pointerType==='touch')return;const rect=card.getBoundingClientRect();px=(event.clientX-rect.left)/rect.width-.5;py=(event.clientY-rect.top)/rect.height-.5;if(!frameId)frameId=requestAnimationFrame(()=>{card.style.transform=`perspective(1100px) rotateX(${-py*7}deg) rotateY(${px*7}deg)`;frameId=0})};
   const leave=()=>{if(frameId)cancelAnimationFrame(frameId);frameId=0;card.style.transform=''};
   card.addEventListener('pointermove',move);card.addEventListener('pointerleave',leave);
   return()=>{card.removeEventListener('pointermove',move);card.removeEventListener('pointerleave',leave);leave()};
  });
  return()=>cleanups.forEach(cleanup=>cleanup());
 },[location.pathname,lowEffects,systemReduced]);
 return <div className="app-frame" ref={frame}><Header/><Suspense fallback={<main className="route-loading" aria-busy="true"><span/><p className="eyebrow">LOADING</p></main>}><Routes><Route path="/" element={<HomePage/>}/><Route path="/meet" element={<NewMeetingPage/>}/><Route path="/meet/:id" element={<MeetingPage/>}/><Route path="*" element={<NotFound/>}/></Routes></Suspense><footer className="site-footer"><div className="footer-brand"><BrandMark mini/><span>ActionMint</span></div><p>Make what was said easier to act on.</p><span className="footer-note"><ShieldCheck size={14}/> Private by default</span></footer>{!token&&<TokenGate onSave={value=>{setAppToken(value);setToken(value)}}/>}</div>;
}
export default function App(){return <BrowserRouter><AppInner/></BrowserRouter>}
