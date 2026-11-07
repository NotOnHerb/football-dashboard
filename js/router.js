// Address-bar routes: #<section>/<view>[?k=v&k=v], where section and view are the slugs of their registry labels:
//   #nfl/matchups   #fantasy/start-sit   #fantasy/rankings?fmt=dyn   #betting/props   #betting/games?lg=cfb
// Opening the page with a route, or changing the hash, goes there. Moving around the page rewrites the hash in place
// (history.replaceState, so Back still leaves the page). A plain load with no hash keeps the default view and leaves
// the address alone until the first click.
var ROUTING=false;  // true once boot is done; until then syncHash does nothing
function parseRoute(h){h=String(h||'').replace(/^#\/?/,'');var i=h.indexOf('?'),path=i<0?h:h.slice(0,i),q=i<0?'':h.slice(i+1),p=path.split('/'),params={};
  q.split('&').forEach(function(kv){if(!kv)return;var j=kv.indexOf('=');try{params[decodeURIComponent(j<0?kv:kv.slice(0,j))]=j<0?'':decodeURIComponent(kv.slice(j+1))}catch(e){}});
  return {sec:(p[0]||'').toLowerCase(),view:(p[1]||'').toLowerCase(),params:params}}
function routeOf(S){var c=(S.current&&guard(S,'current'))||{},V=c.view!=null?findSection(c.view,S.id):null,p=c.params||{},
  qs=Object.keys(p).filter(function(k){return p[k]!=null&&p[k]!==''}).map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(p[k])}).join('&');
  return '#'+slugOf(S)+(V?'/'+slugOf(V):'')+(qs?'?'+qs:'')}
// go(route, hash): show the section and view a parsed route names. An unknown section changes nothing: it is logged
// as a warning and the address goes back to the current view. An unknown view shows the section's current view.
// The view and params wait on the section (S.route) until its data has loaded and its init has run (showSec), so a
// first-load deep link sees the same state a click would, and one whose data failed is applied on the next visit.
function go(r,h){var S=topSections().filter(function(s){return slugOf(s)===r.sec})[0];
  if(!S){console.warn('No section "'+r.sec+'" (address '+h+'); staying where we are.');var C=findSection(st.sec);if(C)try{history.replaceState(null,'',routeOf(C))}catch(e){}return false}
  var V=r.view?viewsOf(S.id).filter(function(v){return slugOf(v)===r.view})[0]:null;
  if(r.view&&!V)console.warn('No view "'+r.view+'" in '+S.label+' (address '+h+'); showing its current view.');
  S.route=[V?V.id:null,r.params||{}];showSec(S.id);return true}
function syncHash(){if(!ROUTING)return;var S=findSection(st.sec);if(!S)return;var h=routeOf(S);
  if(h!==location.hash)try{history.replaceState(null,'',h)}catch(e){}}
function startRouter(){ROUTING=true;if(location.hash&&location.hash!=='#')go(parseRoute(location.hash),location.hash);
  window.addEventListener('hashchange',function(){if(location.hash&&location.hash!=='#')go(parseRoute(location.hash),location.hash)})}
