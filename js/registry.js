// The section registry: every part of the page registers itself here, and the top-level nav (#sec, and #bnav on
// phones) is generated from it.
//
//   register({id, label, parent, dataKeys, needs, init, render})
//     id        unique among its siblings. Top-level sections use the nav codes (nfl, fan, bet); views use the code of
//               their tab button (data-v / data-x), so the existing handlers keep working.
//     label     the name in the nav; its slug is also the route (#betting/props: see router.js).
//     parent    the id of the top-level section a view belongs to. Leave it out for a top-level section, or for a
//               module that isn't in the nav (the player card).
//     dataKeys  the data.json keys it reads, including through functions it calls in other files. They decide which
//               data files load before it runs (see "data shards" below), so a key left out is data that isn't there.
//     needs     ids of top-level sections whose code it uses (the player card draws Betting's prop table): their data
//               loads and their init runs before this section's.
//     init      runs once, after its data loads: at boot when all of it is in data/core.json, else on first visit.
//     render    draws it. For a top-level section: shows its current view.
//   Top-level sections also give icon (svg markup for the phone tab bar), panels (ids of the elements shown exactly
//   while the section is current), viewPanels (ids hidden while it isn't current; its render decides which of them
//   show), wide (true for the wider page), select(view, params) (make a view current, before
//   render; used by the router) and current() -> {view, params} (what the address bar should say).
//
// guard(s, 'init' | 'render' | ...) runs one of those in a try/catch, so one broken section can't take down the rest.
var SECTIONS=[];
function register(s){SECTIONS.push(s);return s}
function topSections(){return SECTIONS.filter(function(s){return !s.parent&&s.panels})}
function viewsOf(id){return SECTIONS.filter(function(s){return s.parent===id})}
function findSection(id,parent){for(var i=0;i<SECTIONS.length;i++){var s=SECTIONS[i];if(s.id===id&&(s.parent||null)===(parent||null))return s}return null}
function slugOf(s){return s.label.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')}

// ---------------- error isolation
// FAILED: the names in the failure line. STALE: one of them failed because its data file is from a newer build.
var FAILED=[],STALE=false;
function guard(s,fn,args){if(!s||typeof s[fn]!=='function')return;
  try{return s[fn].apply(s,args||[])}catch(e){sectionFailed(s,fn,e)}}
// The name shown for a failure: "Parent → View" for a view; for a top-level section, its current view if it has one.
function failName(s){if(s.parent)return (findSection(s.parent)||{label:s.parent}).label+' → '+s.label;
  var V=null;try{var c=s.current&&s.current();V=c&&c.view!=null?findSection(c.view,s.id):null}catch(e){}
  return s.label+(V?' → '+V.label:'')}
// fn 'load' is a data file that didn't load (e.stale: it is from another build); loadOk(s) takes it back off the line.
function sectionFailed(s,fn,e){var name=failName(s);
  console.error('Section "'+name+'" failed in '+fn+(s.dataKeys&&s.dataKeys.length?' (reads '+s.dataKeys.join(', ')+')':'')+':',e);
  if(FAILED.indexOf(name)<0)FAILED.push(name);
  if(fn==='load'){(s.loadFails=s.loadFails||[]).push(name);if(e&&e.stale)STALE=true}
  showFailures()}
function loadOk(s){if(!s.loadFails)return;var gone=s.loadFails;s.loadFails=null;FAILED=FAILED.filter(function(n){return gone.indexOf(n)<0});showFailures()}
function showFailures(){var el=$('hlerr');
  if(!FAILED.length){STALE=false;if(el)el.parentNode.removeChild(el);return}
  if(!el){el=document.createElement('p');el.id='hlerr';el.className='hl';var hl=$('hl');hl.parentNode.insertBefore(el,hl.nextSibling)}
  el.textContent=STALE?'The dashboard was updated after this page opened, so part of it can’t load: '+FAILED.join(', ')+'. Refresh the page to get the new version.'
    :'Part of the page didn’t load: '+FAILED.join(', ')+'. Everything else still works; try refreshing.'}

// ---------------- data shards
// build.py writes data.json whole and also split by top-level key into data/<shard>.json, with data/index.json
// saying which keys each file holds (schema/shards.py). main.js loads index.json and core.json at boot. A top-level
// section's other files load the first time it is shown: its own and its views' dataKeys say which, and the sections
// it needs come first. Then the section's and its views' inits run (once, in script order) and it renders. A section
// whose data is all in core.json inits at boot. So does a module outside the nav (the player card), which calls
// need(itself) before it draws. While a section's data loads, <main> has aria-busy="true" and a "Loading …" line shows
// under the nav. A file that fails to load or takes longer than FETCH_MS is reported like a failed section
// (sectionFailed), and the next visit tries again. Every URL carries ?v=VER.
// Every file carries its build stamp (index.json {build, shards}, a shard {build, data}): a shard from another build
// than core.json, or holding other keys than index.json lists, is refused (the dashboard updated since the page
// opened; the failure line says to refresh), so two days' data never mix. If index.json or core.json can't be
// loaded or disagree, main.js loads data.json whole instead (WHOLE: every key is there, nothing loads later).
var SHARD_OF={},SHARD_KEYS={},SHARD_LOAD={},SHARD_OK={},BUILD=null,WHOLE=false,BUSY=0;
var FETCH_MS=window.FETCH_MS||20000;  // a test can set window.FETCH_MS before the scripts run
function fetchData(path){var c=typeof AbortController==='function'?new AbortController():null,t=c&&setTimeout(function(){c.abort()},FETCH_MS);
  return fetch(path+'?v='+VER,{cache:'no-cache',signal:c?c.signal:undefined}).then(function(r){if(!r.ok)throw new Error(path+' answered '+r.status);return r.json()})
    .then(function(o){clearTimeout(t);return o},function(e){clearTimeout(t);throw e&&e.name==='AbortError'?new Error(path+' took longer than '+FETCH_MS/1000+' s'):e})}
function setIndex(index){BUILD=index.build;Object.keys(index.shards).forEach(function(s){SHARD_KEYS[s]=index.shards[s];index.shards[s].forEach(function(k){SHARD_OF[k]=s})})}
function staleError(msg){var e=new Error(msg);e.stale=true;return e}
// takeShard(name, file): puts a shard file's data in D, if it is from this page's build and holds what index.json lists.
function takeShard(name,o){var p='data/'+name+'.json',got=Object.keys((o&&o.data)||{}),want=SHARD_KEYS[name]||[];
  if(!o||o.build!==BUILD)throw staleError(p+' is from build '+(o&&o.build)+', this page from '+BUILD);
  if(got.length!==want.length||want.some(function(k){return got.indexOf(k)<0}))throw staleError(p+' holds '+got.join(' ')+', index.json lists '+want.join(' '));
  got.forEach(function(k){D[k]=o.data[k]});SHARD_OK[name]=true}
// loadShard(name): a Promise that resolves once data/<name>.json is in D (fetched once; after a failure, again).
function loadShard(name){if(SHARD_OK[name])return Promise.resolve();
  if(!SHARD_LOAD[name])SHARD_LOAD[name]=fetchData('data/'+name+'.json').then(function(o){takeShard(name,o)}).catch(function(e){delete SHARD_LOAD[name];throw e});
  return SHARD_LOAD[name]}
// A top-level section with its views (script order); any other section on its own.
function familyOf(S){return S.parent||!S.panels?[S]:SECTIONS.filter(function(x){return x===S||x.parent===S.id})}
function shardsOf(S){if(WHOLE)return [];var out=[];familyOf(S).forEach(function(x){(x.dataKeys||[]).forEach(function(k){var n=SHARD_OF[k];
  if(!n)throw new Error('no data file holds '+k+' (data/index.json)');if(out.indexOf(n)<0)out.push(n)})});return out}
function hasData(S){try{return shardsOf(S).every(function(n){return SHARD_OK[n]})}catch(e){return false}}
// keyLoaded(k): whether D.k has arrived (tests/test_page.py checks every D.<KEY> read with it).
function keyLoaded(k){return WHOLE||!!SHARD_OK[SHARD_OF[k]]}
function initOnce(s){if(!s.inited){s.inited=true;guard(s,'init')}}
function busy(d){BUSY+=d;var m=document.querySelector('main');if(BUSY>0)m.setAttribute('aria-busy','true');else m.removeAttribute('aria-busy')}
// need(S): a Promise that resolves once S's data (and the sections it needs) has loaded and S and its views have run
// init. S.ready says that has happened, so callers can stay synchronous then.
function need(S){if(S.ready)return Promise.resolve();
  if(!S.loading){busy(1);
    S.loading=Promise.resolve().then(function(){return Promise.all((S.needs||[]).map(function(id){return need(findSection(id))}).concat(shardsOf(S).map(loadShard)))})
      .then(function(){busy(-1);S.ready=true;loadOk(S);familyOf(S).forEach(initOnce)},function(e){busy(-1);S.loading=null;throw e})}
  return S.loading}
// At boot, after core.json: init (in script order) every section whose data is all there, and the modules outside the nav.
function bootSections(){SECTIONS.forEach(function(s){var R=s.parent?findSection(s.parent):s,ok=!(R.needs||[]).length&&hasData(R);
  if(ok)R.ready=true;if(ok||!R.panels)initOnce(s)})}

// ---------------- top-level nav
function buildNav(){var T=topSections();
  $('sec').innerHTML=T.map(function(s){return html`<button data-s="${s.id}" aria-pressed="${s.id===st.sec}">${s.label}</button>`}).join('');
  $('bnav').innerHTML=T.map(function(s){return html`<button data-s="${s.id}" aria-pressed="${s.id===st.sec}">${raw(s.icon||'')}${s.label}</button>`}).join('')}
function wireNav(){$('sec').addEventListener('click',function(e){var s=e.target.dataset.s;if(s)showSec(s)});
  $('bnav').addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;showSec(b.dataset.s);window.scrollTo(0,0)})}
// WANT is the section asked for last, so one whose data arrives after the visitor moved on stays hidden.
var WANT=null;
// whenReady(S, ok, failed): ok() now if S is ready. Otherwise the nav shows S pressed and a "Loading …" line at once,
// and ok() runs once its data has loaded (if S is still the one asked for). If it can't load, the failure is reported
// and failed() runs.
function whenReady(S,ok,failed){WANT=S.id;if(S.ready){loadingNote(null);return ok()}
  pressNav(S.id);loadingNote('Loading '+S.label+'…');
  need(S).then(function(){if(WANT===S.id){loadingNote(null);ok()}},function(e){sectionFailed(S,'load',e);if(WANT===S.id){loadingNote(null);failed()}})}
// showSec(s): shows top-level section s. S.route is a route (from go) waiting to be applied: its select runs first.
// When the data can't load, S shows without content (so the click visibly did something), and the address keeps a
// waiting route, which the next visit applies.
function showSec(s){var S=findSection(s);if(!S||S.parent)return;
  whenReady(S,function(){if(S.route){var r=S.route;S.route=null;guard(S,'select',r)}showPanels(S);guard(S,'render');syncHash()},
    function(){showPanels(S);if(!S.route)syncHash()})}
function pressNav(s){[].forEach.call($('sec').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===s)});[].forEach.call($('bnav').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===s)})}
function showPanels(S){var s=S.id;st.sec=s;pressNav(s);
  topSections().forEach(function(x){x.panels.forEach(function(id){$(id).hidden=x.id!==s});if(x.id!==s)(x.viewPanels||[]).forEach(function(id){$(id).hidden=true})});
  document.querySelector('main').classList.toggle('wide',!!S.wide)}
// loadingNote(text): the short line under the nav while data loads (null removes it).
function loadingNote(text){var el=$('ldsec');if(text==null){if(el)el.parentNode.removeChild(el);return}
  if(!el){el=document.createElement('p');el.id='ldsec';el.className='sub';el.setAttribute('role','status');var nav=$('sec').parentNode;nav.parentNode.insertBefore(el,nav.nextSibling)}
  el.textContent=text}
