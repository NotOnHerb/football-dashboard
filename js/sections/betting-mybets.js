// Betting -> My bets and Results: saved bets (kept in localStorage), grading and the pick ledger.
// Data: ODD.FIN, ODD.LG, LOG.
var BETREG={};
function gBet(g,k,q){var mk=gmk(k),b={id:'g|'+g.id+'|'+mk+'|'+k,k:'g',label:gname(g,k,q),sub:g.a+' at '+g.h,wk:g.wk,t:g.t,a:g.a,h:g.h,mk:mk,sd:k,pt:q.pt,pr:q.pr,bk:q.bk};BETREG[b.id]=b;return b}
function pBet(p,sd,q){var g=gameOf(p.t)||{},b={id:'p|'+p.eid+'|'+p.gid+'|'+p.mk+'|'+sd,k:'p',label:p.n+' '+(sd==='y'?'anytime TD':(sd==='o'?'over ':'under ')+q.pt+' '+p.mk.toLowerCase()),sub:p.t+' vs '+p.opp,wk:g.wk,t:p.ko,gid:p.gid,tm:p.t,mk:p.mk,sd:sd,pt:q.pt,pr:q.pr,bk:q.bk};BETREG[b.id]=b;return b}
function mbLoad(){try{return JSON.parse(store.get('mybets')||'[]')}catch(e){return []}}
function mbSave(L){try{store.set('mybets',JSON.stringify(L))}catch(e){}}
function mbHas(id){return mbLoad().some(function(b){return b.id===id})}
function saveBtn(b,small){var on=mbHas(b.id);return small?' <button class="sv'+(on?' on':'')+'" data-bet="'+esc(b.id)+'" title="'+(on?'Saved to My bets':'Save to My bets')+'" aria-label="Save '+esc(b.label.replace(/"/g,''))+' to My bets">'+(on?'✓':'+')+'</button>':'<button class="back sv2'+(on?' on':'')+'" data-bet="'+esc(b.id)+'">'+(on?'✓ In My bets':'+ Save to My bets')+'</button>'}
var LOGMAX=null;function logMax(){if(LOGMAX==null){LOGMAX=0;Object.keys(D.LOG||{}).forEach(function(k){D.LOG[k].forEach(function(r){if(r[0]>LOGMAX)LOGMAX=r[0]})})}return LOGMAX}
var SIX={'Pass yds':7,'Rush yds':8,'Rec yds':9,'Receptions':6,'Pass TDs':10,'Anytime TD':11};
function gradeBet(b){if(b.res)return b;if(!past(b.t)||b.wk==null)return {res:null};var F=(D.ODD&&D.ODD.FIN)||[],r;
  if(b.k==='g'){var f=F.filter(function(x){return x[0]===b.wk&&x[1]===b.a&&x[2]===b.h})[0];if(!f)return {res:null};var as=f[3],hs=f[4],c;
    if(b.mk==='spread')c=(b.sd==='hs'?hs-as:as-hs)+b.pt;else if(b.mk==='total')c=(as+hs-b.pt)*(b.sd==='ov'?1:-1);else c=(hs-as)*(b.sd==='mh'?1:-1);
    return {res:c>0?'W':c<0?'L':'P',fin:as+'-'+hs}}
  var f2=F.filter(function(x){return x[0]===b.wk&&(x[1]===b.tm||x[2]===b.tm)})[0];if(!f2||logMax()<b.wk)return {res:null};
  var row=((D.LOG||{})[b.gid]||[]).filter(function(x){return x[0]===b.wk})[0];if(!row)return {res:'V'};var v=row[SIX[b.mk]];
  if(b.sd==='y')return {res:v>=1?'W':'L',val:v};var c2=(v-b.pt)*(b.sd==='o'?1:-1);return {res:c2>0?'W':c2<0?'L':'P',val:v}}
function resChip(r){return r==='W'?'<span class="rs w">Won</span>':r==='L'?'<span class="rs l">Lost</span>':r==='P'?'<span class="rs p">Push</span>':r==='V'?'<span class="rs p">Void</span>':'<span class="rs o">Open</span>'}
function units(r,pr){return r==='W'?dec(pr)-1:r==='L'?-1:0}
function pickLabel(r){if(r.k==='x')return r.title+': '+r.legs.map(function(l){return legNeed(l)+(l.res?' ('+({W:'hit',L:'missed',P:'push',V:'void'})[l.res]+')':'')}).join(' + ');if(r.k==='g')return r.mk==='total'?(r.sd==='ov'?'Over ':'Under ')+r.pt+' ('+r.a+' at '+r.h+')':r.mk==='ml'?(r.sd==='mh'?r.h:r.a)+' to win ('+r.a+' at '+r.h+')':(r.sd==='hs'?r.h:r.a)+' '+spf(r.pt)+' ('+r.a+' at '+r.h+')';
  return r.n+' '+(r.sd==='y'?'anytime TD':(r.sd==='o'?'over ':'under ')+r.pt+' '+r.mk.toLowerCase())}
function legNeed(l){if(l.k==='g')return l.mk==='total'?(l.sd==='ov'?'Over ':'Under ')+l.pt+' ('+l.a+' at '+l.h+')':l.mk==='ml'?(l.sd==='mh'?l.h:l.a)+' to win':(l.sd==='hs'?l.h:l.a)+' '+spf(l.pt);
  var noun=NOUN[l.mk]||l.mk.toLowerCase();return l.n+': '+(l.sd==='y'?'scores a touchdown':(l.sd==='o'?(Math.floor(l.pt)+1)+' or more ':(Math.ceil(l.pt)-1)+' or fewer ')+noun)}
function resultsView(){var O=D.ODD,R=O.REC||{},L=(O.LG||[]);
  var h='<div class="tiles">'+[['All picks',R.all],['Game lines',R.g],['Player props',R.p],['Parlays (for fun)',R.x]].map(function(t){var x=t[1]||{w:0,l:0,p:0,u:0};return '<div class="tile"><b>'+x.w+'-'+x.l+(x.p?'-'+x.p:'')+'</b><span>'+t[0]+' · '+(x.u>=0?'+':'')+x.u.toFixed(1)+' units</span></div>'}).join('')+'</div>';
  if(!L.length)return h+'<p class="sub">No picks logged yet. They’re saved each refresh and graded after the games.</p>';
  return h+'<div class="wrap"><table class="olt bt" data-gl="res"><tr><th>Week</th><th>Pick</th><th>Price</th><th>Level</th><th>Result</th><th>Units</th></tr>'+L.map(function(r){var lk=past(r.t);
    return '<tr><td>'+esc(r.wk||'–')+'</td><td class="wr">'+esc(pickLabel(r))+(r.fin?' <small class="pcm">final '+esc(r.fin[0])+'-'+esc(r.fin[1])+'</small>':'')+(r.val!=null?' <small class="pcm">had '+esc(r.val)+'</small>':'')+'</td><td><b>'+am(r.pr)+'</b> <small class="pcm">'+esc(r.bk)+'</small></td><td>'+lvl(r.s)+'</td><td>'+(r.res?resChip(r.res):lk?'<span class="rs o">Locked</span>':'<span class="rs o">Open</span>')+'</td><td>'+(r.res?((r.u>=0?'+':'')+r.u.toFixed(2)):'–')+'</td></tr>'}).join('')+'</table></div><p class="sub" style="margin-top:10px">Open picks can still change until kickoff (the price and line update each refresh, and a pick can drop off). Locked picks are frozen at the last update before kickoff. Void means the player didn’t record a stat that week.</p>'}
function mineView(){var L=mbLoad(),tot={w:0,l:0,p:0,st:0,pf:0,open:0},rows=L.map(function(b){var g=gradeBet(b),r=g.res,st=+b.stake||0,pf=r?st*units(r,b.pr):0;
    if(r==='W')tot.w++;else if(r==='L')tot.l++;else if(r)tot.p++;else tot.open++;if(r){tot.st+=st;tot.pf+=pf}
    return '<tr><td class="wr"><b>'+esc(b.label)+'</b><div class="psub">'+esc(b.sub)+' · '+kick(b.t)+(g.fin?' · final '+esc(g.fin):'')+(g.val!=null?' · had '+esc(g.val):'')+'</div></td><td><b>'+am(b.pr)+'</b> <small class="pcm">'+esc(b.bk)+'</small></td><td><input class="stk" data-id="'+esc(b.id)+'" type="number" min="0" step="1" value="'+esc(b.stake||'')+'" placeholder="$" aria-label="Stake"></td><td>'+resChip(r)+'</td><td>'+(r&&st?(pf>=0?'+$':'-$')+Math.abs(pf).toFixed(2):r?'–':st?'to win $'+(st*(dec(b.pr)-1)).toFixed(2):'–')+'</td><td><button class="sv on" data-del="'+esc(b.id)+'" aria-label="Remove">×</button></td></tr>'});
  if(!L.length)return '<div class="card"><b>No saved bets yet.</b> Tap <b>+</b> next to any line or prop, or “Save to My bets” on a pick. Bets you save grade themselves after the game. They’re saved in this browser only.</div>';
  return '<div class="tiles"><div class="tile"><b>'+tot.w+'-'+tot.l+(tot.p?'-'+tot.p:'')+'</b><span>Record</span></div><div class="tile"><b>'+(tot.pf>=0?'+$':'-$')+Math.abs(tot.pf).toFixed(2)+'</b><span>Profit on settled bets</span></div><div class="tile"><b>'+tot.open+'</b><span>Still open</span></div></div><div class="wrap"><table class="olt bt" data-gl="mine"><tr><th>Bet</th><th>Price</th><th>Stake</th><th>Status</th><th>Profit</th><th></th></tr>'+rows.join('')+'</table></div><p class="sub" style="margin-top:10px">Saved in this browser only. Price is what it was when you saved it; enter the stake you actually bet.</p>'}
function toggleBet(e){var sv=e.target.closest('[data-bet]');if(!sv)return false;e.preventDefault();e.stopPropagation();var id=sv.dataset.bet,bt=BETREG[id],L=mbLoad(),i=L.map(function(x){return x.id}).indexOf(id);
  if(i>-1)L.splice(i,1);else if(bt)L.unshift(Object.assign({saved:new Date().toISOString(),stake:''},bt));mbSave(L);var on=i<0;
  document.querySelectorAll('[data-bet="'+id.replace(/"/g,'\\"')+'"]').forEach(function(b){b.classList.toggle('on',on);b.textContent=b.classList.contains('sv2')?(on?'✓ In My bets':'+ Save to My bets'):(on?'✓':'+')});
  if(BS.v==='mine'&&!$('sb').hidden)renderB();return true}
register({id:'mine',parent:'bet',label:'My bets',dataKeys:['ODD','LOG'],render:renderB});
register({id:'results',parent:'bet',label:'Results',dataKeys:['ODD'],render:renderB});
