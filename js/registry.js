// The section registry: every part of the page registers itself here, and the top-level nav (#sec, and #bnav on
// phones) is generated from it.
//
//   register({id, label, parent, dataKeys, init, render})
//     id        unique among its siblings. Top-level sections use the nav codes (nfl, fan, bet); views use the code of
//               their tab button (data-v / data-x), so the existing handlers keep working.
//     label     the name in the nav; its slug is also the route (#betting/props: see router.js).
//     parent    the id of the top-level section a view belongs to. Leave it out for a top-level section, or for a
//               module that isn't in the nav (the player card).
//     dataKeys  the data.json keys it reads (documentation; named when it fails).
//     init      runs once at boot, after data.json loads.
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
var FAILED=[];
function guard(s,fn,args){if(!s||typeof s[fn]!=='function')return;
  try{return s[fn].apply(s,args||[])}catch(e){sectionFailed(s,fn,e)}}
// The name shown for a failure: "Parent → View" for a view; for a top-level section, its current view if it has one.
function failName(s){if(s.parent)return (findSection(s.parent)||{label:s.parent}).label+' → '+s.label;
  var V=null;try{var c=s.current&&s.current();V=c&&c.view!=null?findSection(c.view,s.id):null}catch(e){}
  return s.label+(V?' → '+V.label:'')}
function sectionFailed(s,fn,e){var name=failName(s);
  console.error('Section "'+name+'" failed in '+fn+(s.dataKeys&&s.dataKeys.length?' (reads '+s.dataKeys.join(', ')+')':'')+':',e);
  if(FAILED.indexOf(name)<0)FAILED.push(name);
  var el=$('hlerr');if(!el){el=document.createElement('p');el.id='hlerr';el.className='hl';var hl=$('hl');hl.parentNode.insertBefore(el,hl.nextSibling)}
  el.textContent='Part of the page didn’t load: '+FAILED.join(', ')+'. Everything else still works; try refreshing.'}

// ---------------- top-level nav
function buildNav(){var T=topSections();
  $('sec').innerHTML=T.map(function(s){return html`<button data-s="${s.id}" aria-pressed="${s.id===st.sec}">${s.label}</button>`}).join('');
  $('bnav').innerHTML=T.map(function(s){return html`<button data-s="${s.id}" aria-pressed="${s.id===st.sec}">${raw(s.icon||'')}${s.label}</button>`}).join('')}
function wireNav(){$('sec').addEventListener('click',function(e){var s=e.target.dataset.s;if(s)showSec(s)});
  $('bnav').addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;showSec(b.dataset.s);window.scrollTo(0,0)})}
function showSec(s){var S=findSection(s);if(!S||S.parent)return;st.sec=s;
  [].forEach.call($('sec').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===s)});[].forEach.call($('bnav').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===s)});
  topSections().forEach(function(x){x.panels.forEach(function(id){$(id).hidden=x.id!==s});if(x.id!==s)(x.viewPanels||[]).forEach(function(id){$(id).hidden=true})});
  document.querySelector('main').classList.toggle('wide',!!S.wide);
  guard(S,'render');syncHash()}
