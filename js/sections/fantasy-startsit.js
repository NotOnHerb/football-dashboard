// Fantasy -> Start / sit: this week's starters by matchup (renderF) and the loaded team's lineup (renderMy),
// the weekly points model (fbase, wkPts) and the lineup optimizer (bestLineup). Data: P, ALW, G, PRI, DY.L.
// ---------------- Fantasy start/sit
var FS={p:'ALL',c:'adj',d:-1};
function grade(m){return m>=1.15?'A':m>=1.05?'B':m>=.95?'C':m>=.85?'D':'F'}
var FSM='me';
function renderMy(){var el=$('fmy');if(!RL.M){var last=null;try{last=JSON.parse(localStorage.getItem('last_league')||'null')}catch(e){}
    if(last&&!RL.auto){RL.auto=1;el.innerHTML='<p class="sub">Loading your team…</p>';autoLoad(last);return}
    el.innerHTML='<div class="card"><b>Load your league to get start/sit help for your team.</b> Open <b>My league</b>, pick Sleeper or ESPN and load it once. After that, this tab remembers it.</div>';return}
  var M=RL.M,me=M.teams.filter(function(T){return T.me})[0];prepM(M);
  if(!me){el.innerHTML='<div class="card">Your team wasn’t found in '+esc(M.name)+'. For ESPN, add your team ID in <b>My league</b>.</div>';return}
  var B=me.best,rec=M.rec,inB={};B.list.forEach(function(s){if(s.e)inB[s.e.p.k]=s.slot});
  var minAt=function(pos){var c=B.list.filter(function(s){return s.e&&ELIG[s.slot].indexOf(pos)>-1}).map(function(s){return s.e.w.pts});return c.length?Math.min.apply(null,c):null};
  var rows=me.ps.filter(function(p){return p.st!=='IR'||true}).map(function(p){var w=wkPts(p.k,rec);if(!w||w.pts==null)return null;var v,why='';
    if(w.opp==='Bye'){v='Bye'}else if(w.out||p.st==='IR'){v='Out'}else if(inB[p.k]){v='Start';why=({SF:'Superflex',WRTE:'WR/TE flex',WRRB:'RB/WR flex'}[inB[p.k]]||inB[p.k])}
    else{var mn=minAt(w.pos);v=mn!=null&&w.pts>=mn-1?'Toss-up':'Sit';if(mn!=null)why=(w.pts-mn>=0?'+':'')+(w.pts-mn).toFixed(1)+' vs your lowest starter there'}
    var now=p.st==='S'?'Starting':p.st==='IR'?'IR':p.st==='Taxi'?'Taxi':'Bench',act=v==='Start'&&now!=='Starting'?'Move in':(v!=='Start'&&now==='Starting'?'Move out':'');
    return {p:p,w:w,v:v,why:why,now:now,act:act}}).filter(Boolean);
  var ord={Start:0,'Toss-up':1,Sit:2,Out:3,Bye:4};rows.sort(function(a,b){return ord[a.v]-ord[b.v]||b.w.pts-a.w.pts});
  var moves=rows.filter(function(r){return r.act});
  var VC={Start:'gA','Toss-up':'gC',Sit:'gD',Out:'gF',Bye:'gF'};
  var h='<p class="sub">'+esc(M.name)+' · '+M.platform+' · '+(rec>=1?'PPR':rec<=0?'Standard':rec===.5?'Half PPR':rec+' per catch')+' scoring. Your best lineup this week: <b>'+f(B.total,1)+'</b> adjusted points ('+nth(me.prk)+' of '+M.teams.length+' in your league).</p>';
  h+=moves.length?'<div class="card" style="margin-bottom:10px"><b>Lineup moves:</b> '+moves.map(function(r){return (r.act==='Move in'?'<span class="up">Start</span> ':'<span class="dn">Bench</span> ')+'<b>'+pName(r.p)+'</b>'}).join(', ')+'.</div>':'<div class="card" style="margin-bottom:10px">Your current lineup already matches the best one. No moves needed.</div>';
  h+='<div class="wrap"><table class="olt"><tr><th>Verdict</th><th>Player</th><th>Opponent</th><th>Season</th><th>Last 3</th><th>Matchup</th><th>Grade</th><th>Adj. pts</th><th>Now</th><th>Why</th></tr>'+rows.map(function(r){var w=r.w;
    return '<tr><td><span class="gr '+VC[r.v]+'" style="padding:0 8px">'+r.v+'</span></td><td class="nm">'+pName(r.p)+' <span class="tag '+w.pos+'">'+w.pos+'</span>'+tags({inj:w.inj,dl:w.dl})+'</td><td>'+w.opp+'</td><td>'+f(w.ppg,1)+'</td><td>'+f(w.l3,1)+'</td><td>'+(w.opp==='Bye'?'–':w.m.toFixed(2)+'×')+'</td><td>'+(w.opp==='Bye'?'–':'<span class="gr g'+w.g+'">'+w.g+'</span>')+'</td><td><b>'+f(w.pts,1)+'</b></td><td>'+r.now+(r.act?' <span class="'+(r.act==='Move in'?'up':'dn')+'">('+r.act.toLowerCase()+')</span>':'')+'</td><td class="wr">'+esc(r.why)+'</td></tr>'}).join('')+'</table></div>';
  h+='<p class="sub">Start means he’s in your best lineup (the spot is under Why). Toss-up means a bench player within 1 point of the starter he’d replace, so trust your gut. Kickers, defenses and IDP aren’t graded yet. To switch teams or leagues, use My league.</p>';
  el.innerHTML=h}
async function autoLoad(last){try{if(last.p==='s'){var user=await slp('user/'+encodeURIComponent(last.u));if(!user||!user.user_id)throw 0;RL.user=user;await fSleeperLeague(last.id)}else{$('fei').value=last.id;$('fet').value=last.t||'';await fEspn()}}catch(e){}
  if(!RL.M)$('fmy').innerHTML='<div class="card">Couldn’t reload your last league. Open <b>My league</b> to load it again.</div>';else if(FV==='s')renderMy()}
function renderF(){$('fmy').hidden=FSM!=='me';$('fall').hidden=FSM!=='all';if(FSM==='me')return renderMy();var W=D.ALW;if(!W||!D.G||!D.G.length){$('ft').innerHTML='<p class="sub" style="padding:14px">No upcoming games or matchup data right now.</p>';return}
  var opp={},when={};D.G.forEach(function(g){opp[g[0]]=g[1];opp[g[1]]=g[0];when[g[0]]='at '+g[1];when[g[1]]='vs '+g[0]});
  var si=st.sc==='std'?1:0,rows=A.filter(function(r){return opp[r[1]]&&['QB','RB','WR','TE'].indexOf(r[2])>-1&&r.dl&&r.dl[1]&&(FS.p==='ALL'||r[2]===FS.p)}).map(function(r){
    var o=opp[r[1]],T=W.T[o],al=T&&T.aa&&T.aa[r[2]],lg=W.lg[r[2]],m=al&&lg?(st.sc==='half'?((al[0]+al[1])/(lg[0]+lg[1])):al[si]/lg[si]):1,base=fbase(r[4],r.l3,r[3],r.gid);
    var x=r.slice();x.inj=r.inj;x.dl=r.dl;x.opp=when[r[1]];x.m=Math.round(m*100)/100;x.base=base==null?null:Math.round(base*10)/10;x.adj=base==null?null:Math.round(base*m*10)/10;x.g=grade(m);x.l3=r.l3;return x});
  rows=sortRows(rows,FS.c,FS.d);
  var cols=[['Player',0],['Pos',2],['Team',1],['Opponent','opp'],['Season',4],['Last 3','l3'],['Base pts','base'],['Matchup','m'],['Grade','g'],['Adj. pts','adj']];
  $('fsub').textContent='This week’s starters, ranked by matchup-adjusted points. Games: '+D.G.map(function(g){return g[0]+' at '+g[1]}).join(', ')+'.';
  $('ft').innerHTML=rows.length?'<table><tr>'+cols.map(function(c){var on=c[1]===FS.c;return '<th tabindex="0" data-c="'+c[1]+'" class="'+(on?'on':'')+'">'+c[0]+(on?(FS.d>0?' ▲':' ▼'):'')+'</th>'}).join('')+'</tr>'+rows.map(function(r){var out=r.inj&&OUTS[r.inj[0]];
    return '<tr><td class="nm">'+r[0]+tags(r)+(out?' <span class="why">Don’t start</span>':'')+'</td><td><span class="tag '+r[2]+'">'+r[2]+'</span></td><td>'+r[1]+'</td><td>'+r.opp+'</td><td>'+f(r[4],1)+'</td><td>'+f(r.l3,1)+'</td><td>'+f(r.base,1)+'</td><td>'+r.m.toFixed(2)+'×</td><td><span class="gr g'+r.g+'">'+r.g+'</span></td><td><b>'+f(r.adj,1)+'</b></td></tr>'}).join('')+'</table>':'<p class="sub" style="padding:14px">No starters match.</p>';
  $('fnote').textContent=''}
function wkPts(k,rec){var x=D.DY.L[k];if(!x)return null;var pos=x[1],tm=x[2],W=D.ALW;if(['QB','RB','WR','TE'].indexOf(pos)<0)return {x:x,pos:pos,pts:null};
  var ppg=x[6]==null?null:rec>=1?x[6]:rec<=0?x[7]:(x[6]+x[7])/2,l3=x[9]==null?null:rec>=1?x[9]:rec<=0?(x[13]==null?x[9]:x[13]):(x[9]+(x[13]==null?x[9]:x[13]))/2;
  var o={x:x,pos:pos,ppg:ppg,l3:l3,inj:x[11],dl:x[12]},opp=null,home=null;(D.G||[]).forEach(function(g){if(g[0]===tm){opp=g[1];home=false}if(g[1]===tm){opp=g[0];home=true}});
  o.opp=opp?(home?'vs ':'at ')+opp:'Bye';var base=ppg==null?0:fbase(ppg,l3,x[8],x[14],rec),m=1;
  if(opp&&W&&W.T[opp]&&W.T[opp].aa&&W.T[opp].aa[pos]){var al=W.T[opp].aa[pos],lg=W.lg[pos];m=rec>=1?al[0]/lg[0]:rec<=0?al[1]/lg[1]:(al[0]+al[1])/(lg[0]+lg[1])}
  o.m=m;o.g=grade(m);o.out=!!(o.inj&&OUTS[o.inj[0]]);o.pts=!opp||o.out?0:Math.round(base*m*10)/10;return o}
function bestLineup(ps,slots,rec){var pool=ps.filter(function(p){return p.st!=='IR'&&p.st!=='Taxi'}).map(function(p){var w=wkPts(p.k,rec);return w&&w.pts!=null?{p:p,w:w}:null}).filter(Boolean).sort(function(a,b){return b.w.pts-a.w.pts});
  var used={},out=[],order=['QB','RB','WR','TE','WRTE','WRRB','FLEX','SF'];
  order.forEach(function(s){for(var i=0;i<(slots[s]||0);i++){var c=pool.filter(function(e){return !used[e.p.k]&&ELIG[s].indexOf(e.w.pos)>-1})[0];if(c){used[c.p.k]=1;out.push({slot:s,e:c})}else out.push({slot:s,e:null})}});
  return {list:out,total:Math.round(out.reduce(function(a,b){return a+(b.e?b.e.w.pts:0)},0)*10)/10,used:used,pool:pool}}
function pName(p){var x=D.DY.L[p.k];return x?x[0]:(p.nm||'Unknown player')}
function prepM(M){M.teams.forEach(function(T){T.best=bestLineup(T.ps,M.slots,M.rec)});M.teams.slice().sort(function(a,b){return b.best.total-a.best.total}).forEach(function(T,i){T.prk=i+1})}
function initF(){
  $('fpos').innerHTML=['ALL','QB','RB','WR','TE'].map(function(p){return '<button data-p="'+p+'" aria-pressed="'+(p==='ALL')+'">'+(p==='ALL'?'All':p)+'</button>'}).join('');
  $('fpos').addEventListener('click',function(e){var p=e.target.dataset.p;if(!p)return;FS.p=p;[].forEach.call($('fpos').children,function(b){b.setAttribute('aria-pressed',b.dataset.p===p)});renderF()});
  $('fsc').addEventListener('click',function(e){var s=e.target.dataset.s;if(s)setSc(s)});
  $('fv').addEventListener('click',function(e){var x=e.target.dataset.x;if(!x)return;FV=x;fShow()});
  $('fmt').addEventListener('click',function(e){var x=e.target.dataset.f;if(!x)return;FMT=x;try{localStorage.setItem('fmt',x)}catch(err){}fShow();if(RL.M)leagueRender()});
  $('ft').addEventListener('click',function(e){var th=e.target.closest('th');if(!th)return;var c=ck(th);if(FS.c===c)FS.d*=-1;else{FS.c=c;FS.d=(c===0||c===2||c===1||c==='opp'||c==='g')?1:-1}renderF()});
  $('sec').addEventListener('click',function(e){var s=e.target.dataset.s;if(s)showSec(s)});
  $('bnav').addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;showSec(b.dataset.s);window.scrollTo(0,0)});
  $('dsp').addEventListener('click',function(e){e.stopPropagation();var o=$('top').classList.toggle('open');this.setAttribute('aria-expanded',o)});
  document.addEventListener('click',function(e){if($('top').classList.contains('open')&&!e.target.closest('#ctl')&&e.target!==$('dsp')){$('top').classList.remove('open');$('dsp').setAttribute('aria-expanded','false')}
    var n=e.target.closest('.note');if(n&&!e.target.closest('a,button,input,select')&&window.matchMedia&&matchMedia('(max-width: 600px)').matches)n.classList.toggle('open')});
}
function fbase(ppg,l3,gp,gid,rec){if(ppg==null)return null;var c=l3!=null?.85*ppg+.15*l3:ppg,pr=D.PRI&&gid&&D.PRI[gid];
  if(pr&&gp){var sc=rec==null?st.sc:(rec>=1?'ppr':rec<=0?'std':'half'),pv=sc==='ppr'?pr[0]:sc==='std'?pr[1]:(pr[0]+pr[1])/2;c=(gp*c+4*pv)/(gp+4)}return c}
