// The player card (modal): bio, this week, game log, key stats, dynasty value, news and props.
// Data: PL, LOG, DY.P, ODD.P, P, X, and through the start/sit model (weekLine) PRI, ALW, G.
// It isn't in the nav, so its data loads the first time a card opens (openCard), with Betting's (its prop table).
// ---------------- Player cards
var PIX=null,PIXDY=null,PCLAST=null;
// The name index covers the dynasty list once it has loaded (PIXDY: the D.DY it was built from).
function pIndex(){PIX={};PIXDY=D.DY;var add=function(n,o){(PIX[n]=PIX[n]||[]).push(o)};
  A.forEach(function(r){add(r[0],{t:'o',r:r,team:r[1],id:D.P[r[2]]&&r.gid})});
  D.X.forEach(function(r){add(r[0],{t:'d',r:r,team:r[1]})});
  if(D.DY)D.DY.P.forEach(function(r){var n=r[0];if(!PIX[n])add(n,{t:'y',r:r,team:r[2]})})}
function age(b){if(!b)return null;var d=new Date(b),n=new Date();return Math.floor((n-d)/31557600000*10)/10}
function weekLine(team,pos,ppg,l3,gp,gid){var W=D.ALW,opp=null,home=null;(D.G||[]).forEach(function(g){if(g[0]===team){opp=g[1];home=false}if(g[1]===team){opp=g[0];home=true}});
  if(!opp)return {opp:'Bye this week'};var si=st.sc==='std'?1:0,al=W&&W.T[opp]&&W.T[opp].aa&&W.T[opp].aa[pos],lg=W&&W.lg[pos],m=al&&lg?(st.sc==='half'?(al[0]+al[1])/(lg[0]+lg[1]):al[si]/lg[si]):1,base=fbase(ppg,l3,gp,gid);
  return {opp:(home?'vs ':'at ')+opp,m:m,g:grade(m),adj:base==null?null:Math.round(base*m*10)/10}}
function logChart(log,avg){var w=Math.max(log.length*44,220),h=120,mx=Math.max.apply(null,log.map(function(x){return x.p}).concat([avg||0,10])),bw=26;
  var T0=16,s='<svg class="gl2" viewBox="0 -'+T0+' '+w+' '+(h+30+T0)+'" width="100%" style="max-width:'+w+'px" role="img" aria-label="Fantasy points by week">';
  log.forEach(function(x,i){var bh=Math.max(2,x.p/mx*h),xx=i*44+9,c=avg!=null&&x.p>=avg?'#2e9e5b':'#d9534f';s+='<rect x="'+xx+'" y="'+(h-bh+4)+'" width="'+bw+'" height="'+bh+'" rx="4" fill="'+c+'" opacity=".85"><title>Week '+esc(x.w)+' vs '+esc(x.o)+': '+esc(x.p)+' pts</title></rect><text x="'+(xx+bw/2)+'" y="'+(h-bh)+'" text-anchor="middle">'+esc(x.p)+'</text><text x="'+(xx+bw/2)+'" y="'+(h+20)+'" text-anchor="middle">W'+esc(x.w)+'</text>'});
  if(avg!=null){var ay=h-avg/mx*h+4;s+='<line x1="0" x2="'+w+'" y1="'+ay+'" y2="'+ay+'" stroke="currentColor" stroke-dasharray="4 4" opacity=".5"/>'}
  return s+'</svg>'}
function cardRows(name){if(!PIX||PIXDY!==D.DY)pIndex();return PIX[name]}
// openCard(name, team, known): opens the card for that player; returns whether a player has that name. The first
// time, the card's data loads first, so the card opens a moment after the click; clicks meanwhile only change which
// card opens (CARDWANT, the latest). Before the dynasty list has loaded, a name not found yet may still be a player
// with dynasty data only: the data loads and the card opens if he is there (the return value is then false). The
// click handler passes known, so a click on a team name never loads the card's data.
var CARDWANT=null;
function openCard(name,team,known){var hit=!!cardRows(name);
  if(CARD.ready){if(hit)drawCard(name,team);return hit}
  if(!hit&&(known||D.DY))return false;
  var first=!CARDWANT;CARDWANT=[name,team];loadingNote('Loading the player card…');
  if(first)need(CARD).then(function(){var w=CARDWANT;CARDWANT=null;loadingNote(null);if(cardRows(w[0]))drawCard(w[0],w[1])},
    function(e){CARDWANT=null;loadingNote(null);sectionFailed(CARD,'load',e)});
  return hit}
function drawCard(name,team){var c=cardRows(name);if(!c)return;var e=c.filter(function(x){return x.team===team})[0]||c[0],r=e.r,gid,pos,tm,h='',tl=[];
  if(e.t==='o'){gid=r.gid;pos=r[2];tm=r[1]}else if(e.t==='d'){gid=r[20];pos=r[2];tm=r[1]}else{gid=r[16];pos=r[1];tm=r[2]}
  var P=(D.PL&&gid&&D.PL[gid])||[],dy=D.DY?D.DY.P.filter(function(x){return x[0]===name&&(x[16]===gid||!gid)})[0]:null,inj=r.inj||(dy&&dy[14]),dl=r.dl||(dy&&dy[15]),a=age(P[4])||(dy&&dy[3]);
  var bio=[D.N[tm]?tm+' '+D.N[tm]:tm,a?'Age '+a:null,P[2]?Math.floor(P[2]/12)+'′'+(P[2]%12)+'″':null,P[3]?P[3]+' lb':null,dy&&dy[4]?'Drafted '+dy[4]+(dy[5]?' round '+dy[5]:''):null,dy&&dy[6]?dy[6]:null].filter(Boolean).join(' · ');
  var hs=safeUrl(P[0]);h+='<div class="pch">'+(hs?'<img src="'+esc(hs)+'" alt="'+esc(name)+'" loading="lazy">':'')+'<div><h2 id="pcn">'+esc(name)+'</h2><div><span class="tag '+esc(pos)+'">'+esc(pos)+'</span>'+tags({inj:inj,dl:dl})+'</div><div class="pcm">'+esc(bio)+'</div></div></div>';
  if(e.t==='o'&&pos!=='K'){var rank=1+A.filter(function(x){return x[2]===pos&&x[3]>=3&&x[4]>r[4]}).length,wk=weekLine(tm,pos,r[4],r.l3,r[3],r.gid);
    tl=[[f(r[4],1),SCL[st.sc]],[f(r.l3,1),'Last 3'],[r.tr==null?'–':(r.tr>0?'+':'')+r.tr.toFixed(1),'Trend'],[r.sn!=null?r.sn+'%':'–','Snap share'],[pos+rank,'Rank at '+pos+' (3+ GP)'],[r[3],'Games']];
    h+='<div class="tiles2">'+tl.map(function(x){return '<div class="tl"><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div>';
    h+='<div class="pcs"><h3>This week</h3><p class="sub" style="margin:0">'+esc(wk.opp)+(wk.m?' · matchup '+wk.m.toFixed(2)+'× <span class="gr g'+wk.g+'">'+wk.g+'</span> · adjusted points <b>'+f(wk.adj,1)+'</b>':'')+'</p>';
    var LG=(D.LOG&&D.LOG[gid])||[];if(LG.length){var lg2=LG.map(function(x){return {w:x[0],o:x[1],p:st.sc==='std'?x[3]:st.sc==='half'?Math.round((x[2]+x[3])*5)/10:x[2],y:x[4],td:x[5],rec:x[6]}});
      h+='<h3>Game log</h3>'+logChart(lg2,r[4])+'<div class="wrap"><table class="olt"><tr><th>Week</th><th>Opp</th><th>Pts</th><th>Yds</th><th>TD</th><th>Rec</th></tr>'+lg2.slice().reverse().map(function(x){return '<tr><td>'+esc(x.w)+'</td><td>'+esc(x.o)+'</td><td><b>'+esc(x.p)+'</b></td><td>'+esc(x.y)+'</td><td>'+esc(x.td)+'</td><td>'+esc(x.rec)+'</td></tr>'}).join('')+'</table></div>'}
    var pc=D.PC[pos]||[],ks=pc.slice(5,13);if(ks.length)h+='<h3>Key stats</h3><div class="tiles2">'+ks.map(function(s,i){return '<div class="tl"><b>'+f(r[4+5+i],s[1])+'</b><span>'+esc(s[0])+'</span></div>'}).join('')+'</div>';
    h+='</div>'}
  else if(e.t==='o'&&pos==='K'){h+='<div class="tiles2">'+[[f(r[4],1),'Pts/g'],[r[9],'FG made'],[f(r[11],1)+'%','FG %'],[r[12],'Long'],[r[15],'50+'],[r[3],'Games']].map(function(x){return '<div class="tl"><b>'+esc(x[0]==null?'–':x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div>'}
  else if(e.t==='d'){h+='<div class="tiles2">'+[[f(r[16],1),'IDP/g'],[r[4],'Tackles'],[f(r[8],1),'Sacks'],[r[9],'QB hits'],[r[10],'INT'],[r[11],'Passes defended'],[r.sn!=null?r.sn+'%':'–','Snap share'],[r[3],'Games']].map(function(x){return '<div class="tl"><b>'+esc(x[0]==null?'–':x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div>'}
  if(dy){h+='<div class="pcs"><h3>Dynasty</h3><div class="tiles2">'+[[dy[7].toLocaleString(),'Value (1QB)'],[dy[8].toLocaleString(),'Value (Superflex)'],[dy[10]!=null?f(dy[10],1):'–','PPR/g this season'],[dy[3]!=null?dy[3]:'–','Age']].map(function(x){return '<div class="tl"><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div></div>'}
  h+='<div class="pcs"><h3>Latest news</h3><div id="pcnews"><p class="sub">'+(P[1]?'Loading news from ESPN…':'No news source linked for this player yet.')+'</p></div></div>';
  var myp=(D.ODD&&D.ODD.P&&gid)?D.ODD.P.filter(function(x){return x.gid===gid}):[];
  h+='<div class="pcs"><h3>Betting</h3>'+(myp.length?propTable(myp,false):'<p class="sub">No props posted for him yet this week. Yardage props usually show up midweek.</p>')+'</div>';
  $('pcb').innerHTML=h;var im=$('pcb').querySelector('.pch img');if(im)im.addEventListener('error',function(){this.style.visibility='hidden'});PCLAST=document.activeElement;$('pc').hidden=false;document.body.style.overflow='hidden';$('pcx').focus();
  if(P[1])cardNews(P[1],name);return true}
async function cardNews(eid,name){var el=$('pcnews');try{var res=await fetch('https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/'+eid+'/overview');if(!res.ok)throw new Error(res.status);var o=await res.json();if(!$('pcnews')||$('pcn').textContent!==name)return;
  var rw=o.rotowire,nw=(o.news||[]).slice(0,6),fz=o.fantasy||{},h='';
  var po=typeof fz.percentOwned==='number'?fz.percentOwned:null;if(po!=null)h+='<p class="sub" style="margin-top:0">Rostered in '+po.toFixed(1)+'% of ESPN leagues.</p>';
  if(rw&&rw.headline)h+='<div class="rw"><b>'+esc(rw.headline)+'</b>'+(rw.story?'<div style="margin-top:6px">'+esc(rw.story.length>420?rw.story.slice(0,420).replace(/\s+\S*$/,'')+'…':rw.story)+'</div>':'')+'<div class="pcm" style="margin-top:6px">Fantasy note from RotoWire, via ESPN</div></div>';
  if(nw.length)h+='<ul class="adv nws">'+nw.map(function(n){var href=safeUrl(n.links&&n.links.web&&n.links.web.href),d=n.published?new Date(n.published).toLocaleDateString(undefined,{month:'short',day:'numeric'}):'';return '<li>'+(href?'<a href="'+esc(href)+'" target="_blank" rel="noopener">'+esc(n.headline)+'</a>':esc(n.headline))+' <small>'+esc(d)+'</small></li>'}).join('')+'</ul><p class="pcm">Headlines from ESPN. Some are general stories that mention him.</p>';
  el.innerHTML=h||'<p class="sub">No recent news for this player.</p>'}
  catch(err){if($('pcnews'))el.innerHTML='<p class="sub">News isn’t available right now. Try again in a minute.</p>'}}
function closeCard(){$('pc').hidden=true;document.body.style.overflow='';$('pcb').innerHTML='';if(PCLAST&&PCLAST.focus)PCLAST.focus()}
function initCards(){$('pcx').onclick=closeCard;$('pc').addEventListener('click',function(e){if(e.target===$('pc'))closeCard()});
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!$('pc').hidden)closeCard()});
  document.querySelector('main').addEventListener('click',function(e){var el=e.target.closest('td.nm, table b');if(!el||e.target.closest('th'))return;
    var nm='';el.childNodes.forEach(function(n){if(n.nodeType===3)nm+=n.textContent});nm=nm.trim();if(!nm)return;
    var tr=el.closest('tr'),team=null;if(tr)[].forEach.call(tr.cells,function(c){var t=c.textContent.trim();if(D.N[t])team=t});
    if(openCard(nm,team,true)){e.stopPropagation()}},true);
  document.querySelector('main').addEventListener('keydown',function(e){if(e.key!=='Enter')return;var el=e.target.closest&&e.target.closest('td.nm');if(el){el.click();e.preventDefault()}})}
var CARD=register({id:'card',label:'Player card',dataKeys:['PL','LOG','DY','PRI','ODD','P','X','N','PC','ALW','G'],needs:['bet'],init:initCards});
