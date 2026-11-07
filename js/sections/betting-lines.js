// Betting -> Picks, Games and Props, the Betting view switch (renderB, initB) and their cards and tables.
// Data: ODD.
// ---------------- Betting
var BS={lg:(function(){try{return store.get('blg')||'nfl'}catch(e){return 'nfl'}})(),v:'picks',book:(function(){try{return store.get('book')||'best'}catch(e){return 'best'}})(),mk:'ALL',gm:'ALL',q:'',lo:false,more:false};
var BK={Pinnacle:'PIN',DraftKings:'DK',FanDuel:'FD',BetMGM:'MGM',Caesars:'CZR','ESPN BET':'ESPN',Fanatics:'FAN',BetRivers:'BR','Hard Rock':'HR',Bovada:'BOV',BetOnline:'BOL',LowVig:'LV',BetUS:'BUS',MyBookie:'MB','Bally Bet':'BAL'};
function am(x){return x==null?'–':esc((x>0?'+':'')+x)}
function spf(x){return x==null?'–':x===0?'PK':esc((x>0?'+':'')+x)}
function pct(x,d){return x==null?'–':(x*100).toFixed(d||0)+'%'}
function ago(iso){if(!iso)return 'not yet';var m=Math.round((Date.now()-new Date(iso))/60000);return m<2?'just now':m<60?m+' min ago':m<1440?Math.round(m/60)+' hr ago':Math.round(m/1440)+' days ago'}
function kick(iso){return new Date(iso).toLocaleString(undefined,{weekday:'short',hour:'numeric',minute:'2-digit'})}
function bkn(b,short){return BS.book==='best'?' <small class="pcm">'+esc(short?(BK[b]||b):b)+'</small>':''}
function heat(x,full){if(!COLORS||x==null||!isFinite(x))return '';var a=Math.min(1,Math.abs(x)/full);if(a<.15)return '';return ' style="background:color-mix(in srgb,'+(x>0?'#2e9e5b':'#d9534f')+' '+Math.round(8+a*30)+'%,var(--panel))"'}
function bgrade(fac){var g=fac>=1.12?'A':fac>=1.04?'B':fac>=.96?'C':fac>=.88?'D':'F';return '<span class="gr g'+g+'" title="Matchup factor '+fac.toFixed(2)+'">'+g+'</span>'}
function vchip(v){return v==null?'':v>=RU().val[0]&&v<=RU().stale?' <span class="vch">+'+(v*100).toFixed(1)+'% value</span>':''}
function lvl(s){var l=Math.min(3,Math.max(1,s));return '<span class="lvl o">'+['','I','II','III'][l]+'</span>'}
function gname(g,k,q){var t=k==='hs'||k==='mh'?g.h:g.a;return k==='ov'?'Over '+q.pt:k==='un'?'Under '+q.pt:k[0]==='m'?t+' to win':t+' '+spf(q.pt)}
function dots(p,line){return '<span class="hd">'+p.v.slice(-8).map(function(v){var c=line==null?(v[2]>=1?'y':'n'):v[2]>line?'y':v[2]<line?'n':'';return '<i class="'+c+'" title="'+esc('Wk '+v[0]+' vs '+v[1]+': '+v[2])+'"></i>'}).join('')+'</span>'}
function pname(p,x){var s=x.b;return x.td?'Anytime TD':(s.dir>0?'Over ':'Under ')+s.q.pt+' '+p.mk}
function propTips(mk){var td=mk==='Anytime TD',all=mk==='ALL',n=all?'the stat in that row':(NOUN[mk]||mk),bk=BS.book==='best'?'':' at '+BS.book;
  var lean='Our lean when our chance beats what the price needs by 4+ points: I (4+), II (7+), III (10+)';
  if(td)return {Player:'Player, his team and his opponent',Prop:'The bet type',Line:'There’s no number to beat: he just has to score',Lean:lean+'. Not given above +300, where books usually know something we don’t','Our chance':'Our chance he scores: half from our usage model (his carries and targets per game), half from the sportsbooks’ odds with their cut taken out','Typical game':'What our usage model alone says, before blending with the odds','Last games':'His recent games: green means he scored, red means he didn’t (hover a bar for the week)','Hit rate':'Games this season he scored a touchdown','Opp grade':'How many touchdowns this opponent gives up to his position: A soft, F tough',Over:'Price for “yes, he scores”'+bk+', and the chance you need to break even at that price. Tap + to save',Under:'Not offered for anytime TD','Price value':'Not available for anytime TD: books only post the yes side'};
  return {Player:'Player, his team and his opponent',Prop:'The bet type',Line:'The number to beat for '+n+(bk||' (the best line across books)'),Lean:lean,'Our chance':'Our chance he goes over the line: half from our projection and how much his kind of stat swings game to game, half from the sportsbooks’ fair odds. Green leans over, red leans under','Typical game':'His typical game for '+n+': half his games should land above it, half below. Built from 85% season average + 15% last 3 games, plus last season early on, adjusted for the opponent','Last games':'His '+n+' in recent games against this line: green over, red under (hover a bar for the number)','Hit rate':'Games this season his '+n+' went over this line','Opp grade':'How soft this opponent is against his position'+(all?'':' for '+n)+': A soft, F tough',Over:'Price to bet the over'+bk+'. Tap + to save it to My bets',Under:'Price to bet the under'+bk+'. Tap + to save it to My bets','Price value':'How much better this price is than a fair bet, using fair odds from Pinnacle (the sharpest book) or the middle of all books. 2.5%+ counts'}}
function propTable(list,showTeam){var rows=list.map(pa).filter(Boolean);
  if(!rows.length)return '<p class="sub" style="padding:10px 0">'+esc(BS.book==='best'?'No props match.':'No props here at '+BS.book+'. Try "Best available".')+'</p>';
  rows.sort(function(a,b){return b.s-a.s||(b.b.e||0)-(a.b.e||0)});
  var mks={};rows.forEach(function(x){mks[x.p.mk]=1});var TP=propTips(Object.keys(mks).length===1?Object.keys(mks)[0]:'ALL');
  return '<div class="wrap"><table class="olt bt pt"><tr>'+['Player','Prop','Line','Lean','Our chance','Typical game','Last games','Hit rate','Opp grade','Over','Under','Price value'].map(function(h){return '<th data-tip="'+esc(TP[h])+'">'+h+'</th>'}).join('')+'</tr>'+rows.map(function(x){var p=x.p,a=ag(p.gid);
    var nm='<td class="nm">'+esc(p.n)+tags(a)+(showTeam?'<div class="psub">'+esc(p.t)+' vs '+esc(p.opp)+'</div>':'')+'</td><td>'+esc(p.mk)+'</td>';
    if(x.td)return '<tr>'+nm+'<td>Yes</td><td>'+(x.ls?lvl(x.ls)+' Yes':'–')+'</td><td'+heat(x.d,.15)+'><b>'+pct(x.P)+'</b></td><td>'+(p.pj==null?'–':'usage model '+pct(p.pj))+'</td><td>'+dots(p,null)+'</td><td>'+x.hits+' of '+x.n+' scored</td><td>'+bgrade(p.fac)+'</td><td><b>'+am(x.q.pr)+'</b>'+bkn(x.q.bk,1)+' <small class="pcm">needs '+pct(x.im)+'</small>'+saveBtn(pBet(p,'y',x.q),1)+'</td><td>–</td><td>–</td></tr>';
    var o=x.o,u=x.u,b=x.b,ln=(o||u).q.pt,pov=o?o.P:(u&&u.P!=null?1-u.P:null);
    return '<tr>'+nm+'<td>'+esc(ln)+'</td><td>'+(b.ls?lvl(b.ls)+' '+(b.dir>0?'Over':'Under'):'–')+'</td><td'+heat(pov==null?null:pov-.5,.2)+'><b>'+(pov==null?'–':pct(pov)+' over')+'</b></td><td>'+(p.md==null?'–':f(p.md,1))+'</td>'+
      '<td>'+dots(p,ln)+'</td><td'+heat(o?o.h-.5:null,.4)+'>'+(o?Math.round(o.h*x.n)+' of '+x.n+' over':'–')+'</td><td>'+bgrade(p.fac)+'</td><td>'+(o?(o.q.pt!==ln?esc(o.q.pt)+' ':'')+'<b>'+am(o.q.pr)+'</b>'+bkn(o.q.bk,1)+saveBtn(pBet(p,'o',o.q),1):'–')+'</td><td>'+(u?(u.q.pt!==ln?esc(u.q.pt)+' ':'')+'<b>'+am(u.q.pr)+'</b>'+bkn(u.q.bk,1)+saveBtn(pBet(p,'u',u.q),1):'–')+'</td><td>'+(b.vs>0?'<span class="vch">'+(b.dir>0?'Over':'Under')+' +'+(b.v*100).toFixed(1)+'%</span>':'–')+'</td></tr>'}).join('')+'</table></div>'}
function rec(r){return r[0]+'-'+r[1]+(r[2]?'-'+r[2]:'')}
var NOUN={'Pass yds':'passing yards','Rush yds':'rushing yards','Rec yds':'receiving yards','Receptions':'catches','Pass TDs':'passing TDs','Anytime TD':'touchdowns'};
function nPts(x){var r=Math.round(Math.abs(x));return r<1?'less than a point':r===1?'about 1 point':'about '+r+' points'}
function winsBy(m,g){return Math.abs(m)<1?'a toss-up':(m>0?g.h:g.a)+' winning by '+nPts(m)}
function covered(r){var n=r[0]+r[1]+r[2];return esc(r[0]+' of '+n+(r[2]?' ('+r[2]+(r[2]>1?' pushes':' push')+')':''))}
function bookLine(g){var s=g.fair&&g.fair.s?g.fair.s[0]:null,o=g.fair&&g.fair.o?g.fair.o[0]:null;return (s==null?'':(s===0?'even':s<0?g.h+' by '+(-s):g.a+' by '+s))+(o!=null?', '+o+' total points':'')}
function needTxt(g,k,q){var t=k==='hs'||k==='mh'?g.h:g.a;
  if(k==='ov')return Math.floor(q.pt)+1+' or more total points';if(k==='un')return Math.ceil(q.pt)-1+' or fewer total points';if(k[0]==='m')return t+' wins the game';
  if(q.pt>0)return t+' wins, or loses by '+(Math.ceil(q.pt)-1)+' or fewer';if(q.pt<0)return t+' wins by '+(Math.floor(-q.pt)+1)+' or more';return t+' wins (a tie refunds the bet)'}
function moveTxt(g,which){var m=g.mv||[];if(m.length<2)return '';var a=m[0],b=m[m.length-1],t=[],d=new Date(a[0]+'Z').toLocaleDateString(undefined,{weekday:'long'}),sl=function(v){return v===0?'even':v<0?esc(g.h)+' -'+(-v):esc(g.a)+' -'+v};
  if(which!=='o'&&a[1]!=null&&b[1]!=null&&a[1]!==b[1])t.push('the spread went from '+sl(a[1])+' to '+sl(b[1]));if(which!=='s'&&a[2]!=null&&b[2]!=null&&a[2]!==b[2])t.push('the total went from '+esc(a[2])+' to '+esc(b[2]));
  return t.length?'<b>Line movement:</b> since '+d+', '+t.join(' and ')+'.':''}
function whyG(g,x){var w=[],q=x.q,fr=gfair(g,x.k),k=x.k,t=k==='hs'||k==='mh'?g.h:g.a,mk=gmk(k),c=g.ctx||{};
  var pin=((g.fair||{}).ref||{})[mk==='ml'?'m':mk==='total'?'o':'s']==='Pinnacle',ref=pin?'Pinnacle (the sharpest sportsbook)':'the other sportsbooks';
  w.push('<b>What you need:</b> '+esc(needTxt(g,k,q))+'.');
  if(x.v!=null){if(x.vs>0){var pct_=(x.v*100).toFixed(1)+'%';
      if(fr&&fr.pt!=null&&fr.pt!==q.pt){var d=Math.abs(q.pt-fr.pt);w.push('<b>Better number:</b> '+esc(q.bk)+' gives you '+esc(mk==='total'?(k==='ov'?'the over at ':'the under at ')+q.pt:t+' '+spf(q.pt))+'. '+ref[0].toUpperCase()+ref.slice(1)+' only '+esc(mk==='total'?'offers '+fr.pt:'gives '+t+' '+spf(fr.pt))+'. Those extra '+d+' points make this bet worth about <b>'+pct_+' more</b> than a fair bet over time.')}
      else w.push('<b>Better price:</b> '+am(q.pr)+' at '+esc(q.bk)+' pays more than it should. Compared with '+ref+', it’s worth about <b>'+pct_+' more</b> than a fair bet over time.')}
    else w.push('<b>Price:</b> about fair compared with '+ref+'.')}
  if(g.mod&&mk==='spread'){var me=x.me;w.push('<b>Our model:</b> expects '+esc(winsBy(g.mod.m,g))+'. '+(me>=1?'That clears '+esc(t)+' '+spf(q.pt)+' with '+nPts(me)+' to spare.':me<=-1?'That falls '+nPts(me)+' short of covering.':'That’s right on the line.'))}
  if(g.mod&&mk==='total')w.push('<b>Our model:</b> expects about '+Math.round(g.mod.t)+' total points. (We treat this as a hint only; our total predictions haven’t been reliable.)');
  if(g.mod&&mk==='ml')w.push('<b>Our model:</b> gives '+esc(t)+' about a '+Math.round((k==='mh'?g.mod.wp:1-g.mod.wp)*100)+'% chance to win.');
  var wx=wxTxt(g);if(wx&&mk==='total')w.push('<b>Weather:</b> '+wx+'.');
  if(c.a&&c.h){if(mk==='total')w.push('<b>This season:</b> '+esc(g.a)+' games went over the total in '+covered(c.a.ou)+'; '+esc(g.h)+' games in '+covered(c.h.ou)+'.');
    else w.push('<b>This season:</b> '+esc(g.a)+' covered the spread in '+covered(c.a.ats)+' games; '+esc(g.h)+' in '+covered(c.h.ats)+'.')}
  var mv=moveTxt(g,mk==='total'?'o':'s');if(mv)w.push(mv);return w}
function whyP(p,x){var w=[],b=x.b,noun=esc(NOUN[p.mk]||p.mk.toLowerCase());
  if(x.td){w.push('<b>What you need:</b> he scores a touchdown.');
    w.push('<b>Our chance:</b> about '+pct(x.P)+' he scores. Our usage model says '+pct(p.pj)+(p.use?' (he averages '+esc(p.use[0])+' carries and '+esc(p.use[1])+' targets a game)':'')+'; the odds, with the sportsbook’s cut taken out, say about '+pct(x.pf)+'. We split the difference. At '+am(x.q.pr)+' you need '+pct(x.im)+' to break even.');
    w.push('<b>Track record:</b> scored in '+x.hits+' of '+x.n+' games '+dots(p,null))}
  else{var ov=b.dir>0,need=ov?(Math.floor(b.q.pt)+1)+' or more':(Math.ceil(b.q.pt)-1)+' or fewer';
    w.push('<b>What you need:</b> '+need+' '+noun+'.');
    if(b.P!=null)w.push('<b>Our chance:</b> about '+pct(b.P)+' he goes '+(ov?'over ':'under ')+esc(b.q.pt)+'. Our projection says '+pct(b.po)+', the sportsbooks’ fair odds say '+pct(b.fo)+', and we split the difference. At '+am(b.q.pr)+' you need '+pct(i2p(b.q.pr))+' to break even.');
    if(p.md!=null)w.push('<b>Typical game:</b> about '+f(p.md,1)+' '+noun+' (half his games land above, half below). He averages '+esc(p.avg)+' this season and '+esc(p.l3)+' over his last 3.');
    w.push('<b>Track record:</b> went '+(ov?'over ':'under ')+esc(b.q.pt)+' in '+Math.round(b.h*x.n)+' of '+x.n+' games '+dots(p,b.q.pt));
    var g_=gameOf(p.t),wx=g_&&g_.ctx&&g_.ctx.wx;if(wx&&wx.w>=15&&/Pass|Rec/.test(p.mk))w.push('<b>Weather:</b> wind around '+wx.w+' mph at kickoff, which can cut down passing.');
    if(b.vs>0)w.push('<b>Better price:</b> '+am(b.q.pr)+' at '+esc(b.q.bk)+' is worth about <b>'+(b.v*100).toFixed(1)+'% more</b> than a fair bet over time.')}
  if(Math.abs(p.fac-1)>=.04)w.push('<b>Matchup:</b> '+esc(p.opp)+' gives up about '+Math.abs(Math.round((p.fac-1)*200))+'% '+(p.fac>1?'more':'fewer')+' '+(/TD/.test(p.mk)?'touchdowns':p.mk==='Receptions'?'catches':'yards')+' to '+esc(p.pos)+'s than an average defense '+bgrade(p.fac));
  return w}
// The picks to show for the book shown: the build's ODD.PK (best available) or ODD.PKB[book], in the build's order,
// minus games already started. Each becomes a card row {t,g|p,x,s}: x is its ODD.G / ODD.P row scored by gside / pa
// for display, s the build's level. A pick whose row is not in this week's lines is skipped with a console warning; a
// card whose quote differs from the pick's, or that had to use another player's row, is shown with a warning. Returns
// null (with a warning) when this data has no pick list for the book shown.
function pickList(){var O=D.ODD,src=BS.book==='best'?O.PK:(O.PKB||{})[BS.book],G={},P={},used=[],L=[];
  if(!src){console.warn('No pick list for '+(BS.book==='best'?'best available':BS.book)+' in this update');return null}
  O.G.forEach(function(g){G[g.id]=g});
  O.P.forEach(function(p){var id='p|'+p.eid+'|'+p.gid+'|'+p.mk;(P[id]=P[id]||[]).push(p)});
  function free(p){return used.indexOf(p)<0}
  src.forEach(function(k){if(past(k.t))return;var c=null,x,q;
    if(k.k==='g'){var g=G[k.eid];x=g&&gside(g,k.sd);if(x){c={t:'g',g:g,x:x,s:k.s};q=x.q}}
    else{var M=(P['p|'+k.eid+'|'+k.gid+'|'+k.mk]||[]).filter(free),p=M.filter(function(r){return r.n===k.n})[0]||M[0];x=p&&pa(p);
      if(p&&p.n!==k.n&&M.length>1)console.warn('Pick '+k.id+': no row for '+k.n+'; showing '+p.n);
      if(x&&!x.td)x=(x.b=k.sd==='o'?x.o:x.u)?x:null;if(x){used.push(p);c={t:'p',p:p,x:x,s:k.s};q=x.b.q}}
    if(!c){console.warn('Pick '+k.id+' is not in this week’s lines; skipped');return}
    if(q.pt!==k.pt||q.pr!==k.pr||q.bk!==k.bk)console.warn('Pick '+k.id+': the page quotes '+[q.pt,q.pr,q.bk].join(' ')+', the build '+[k.pt,k.pr,k.bk].join(' '));
    L.push(c)});
  return L}
function pickCard(c,hero){var h;
  if(c.t==='g'){var g=c.g,x=c.x;h='<div class="bc l'+Math.min(3,c.s)+(hero?' hero':'')+'">'+(hero?'<div class="bck">Pick of the week</div>':'')+'<div class="bch">'+lvl(c.s)+'<span class="bct">'+esc(gname(g,x.k,x.q))+'</span></div><div class="bcp"><b>'+am(x.q.pr)+'</b> '+esc(x.q.bk)+' · '+esc(g.a)+' at '+esc(g.h)+' · '+kick(g.t)+'</div><ul class="bcw">'+whyG(g,x).map(function(w){return '<li>'+w+'</li>'}).join('')+'</ul>'+saveBtn(gBet(g,x.k,x.q))+'</div>'}
  else{var p=c.p,x=c.x,b=x.b;h='<div class="bc l'+Math.min(3,c.s)+(hero?' hero':'')+'">'+(hero?'<div class="bck">Pick of the week</div>':'')+'<div class="bch">'+lvl(c.s)+'<span class="bct"><a href="#" class="pn" data-n="'+esc(p.n)+'" data-t="'+esc(p.t)+'">'+esc(p.n)+'</a> '+esc(pname(p,x))+'</span></div><div class="bcp"><b>'+am(b.q.pr)+'</b> '+esc(b.q.bk)+' · '+esc(p.t)+' vs '+esc(p.opp)+(gameOf(p.t)?' · '+kick(gameOf(p.t).t):'')+'</div><ul class="bcw">'+whyP(p,x).map(function(w){return '<li>'+w+'</li>'}).join('')+'</ul>'+saveBtn(pBet(p,x.td?'y':(b.dir>0?'o':'u'),b.q))+'</div>'}
  return h}
function gameCard(g){var c=g.ctx||{},S={};['hs','as','ov','un','mh','ma'].forEach(function(k){S[k]=gside(g,k)});
  function cell(k,lab){var x=S[k];if(!x)return '<td>–</td>';var q=x.q;return '<td'+heat(x.v!=null&&x.v>=.02?x.v:null,.06)+'>'+(lab?lab+' ':'')+(q.pt!=null&&k[0]!=='o'&&k[0]!=='u'?spf(q.pt)+' ':q.pt!=null?esc(q.pt)+' ':'')+'<b>'+am(q.pr)+'</b>'+bkn(q.bk,1)+vchip(x.vs>0?x.v:null)+(x.ms?' <span class="mch">model</span>':'')+saveBtn(gBet(g,k,q),1)+'</td>'}
  var wp=g.fair&&g.fair.m!=null?g.fair.m:null,mw=g.mod?g.mod.wp:null,np=D.ODD.P.filter(function(p){return p.t===g.a||p.t===g.h}).length;
  var tags_=[];if(c.div)tags_.push('Division game');if(c.rest&&(c.rest[0]!=null&&c.rest[0]<=5||c.rest[1]!=null&&c.rest[1]<=5))tags_.push('Short week');if(c.rest&&c.rest[0]!=null&&c.rest[1]!=null&&Math.abs(c.rest[0]-c.rest[1])>=3)tags_.push(esc(c.rest[0]>c.rest[1]?g.a:g.h)+' rested '+Math.abs(c.rest[0]-c.rest[1])+' more days');if(c.roof&&c.roof!=='outdoors')tags_.push(c.roof==='dome'?'Dome':esc(c.roof));var wx=wxTxt(g);if(wx)tags_.push(wx);
  return '<div class="gc"><div class="gch"><div><div class="gt">'+esc(g.a)+' <small>at</small> '+esc(g.h)+'</div><div class="pcm">'+kick(g.t)+(tags_.length?' · '+tags_.join(' · '):'')+'</div></div>'+
   (wp!=null?'<div class="wpw"><div class="wpb"><span style="width:'+Math.round((1-wp)*100)+'%" class="wa">'+esc(g.a)+' '+Math.round((1-wp)*100)+'%</span><span style="width:'+Math.round(wp*100)+'%" class="wh">'+Math.round(wp*100)+'% '+esc(g.h)+'</span>'+(mw!=null?'<i style="left:'+Math.round((1-mw)*100)+'%" title="Our model: '+esc(g.h)+' '+Math.round(mw*100)+'%"></i>':'')+'</div><div class="pcm" style="font-size:12px;text-align:right">Win chance from the odds · tick = our model</div></div>':'')+'</div>'+
   '<div class="wrap"><table class="bt gmt" data-gl="gcard"><tr><th></th><th>'+esc(g.a)+'</th><th>'+esc(g.h)+'</th></tr><tr><td>Spread</td>'+cell('as')+cell('hs')+'</tr><tr><td>Total</td>'+cell('ov','O')+cell('un','U')+'</tr><tr><td>Moneyline</td>'+cell('ma')+cell('mh')+'</tr></table></div>'+
   '<div class="gmeta">'+(bookLine(g)?'<span><b>Sportsbooks expect:</b> '+esc(bookLine(g))+'.</span>':'')+(g.mod?'<span><b>Our model expects:</b> '+esc(winsBy(g.mod.m,g))+', about '+Math.round(g.mod.t)+' total points.</span>':'')+(c.a&&c.h?'<span><b>Covered the spread this season:</b> '+esc(g.a)+' in '+covered(c.a.ats)+' games; '+esc(g.h)+' in '+covered(c.h.ats)+'.</span><span><b>Went over the total:</b> '+esc(g.a)+' games '+covered(c.a.ou)+'; '+esc(g.h)+' games '+covered(c.h.ou)+'.</span><span><b>Points per game:</b> '+esc(g.a)+' scores '+esc(c.a.pf)+' and allows '+esc(c.a.pa)+'; '+esc(g.h)+' scores '+esc(c.h.pf)+' and allows '+esc(c.h.pa)+'.</span>':'')+(moveTxt(g)?'<span>'+moveTxt(g)+'</span>':'')+'</div>'+
   (np?'<button class="back gprop" data-gm="'+esc(g.h)+'">Player props for this game ('+np+')</button>':'')+'</div>'}
// ---- weather, saved bets, grading, combos, line moves
function wxTxt(g){var w=g&&g.ctx&&g.ctx.wx;if(!w||w.t==null)return '';return w.t+'°F, wind '+w.w+' mph'+(w.g!=null&&w.g>=w.w+8?' (gusts '+w.g+')':'')+(w.pp!=null&&w.pp>=30?', '+w.pp+'% rain/snow':'')+(w.w>=15?' <span class="wxw">windy</span>':'')}
function parlayCard(x){return '<div class="bc l2"><div class="bck" style="color:var(--b)">'+esc(x.title)+'</div><div class="bch"><span class="bct">'+x.legs.length+' legs · '+am(x.pr)+'</span></div><div class="bcp"><b>'+am(x.pr)+'</b> '+esc(x.bk)+' · our chance about '+pct(x.pc)+', needs '+pct(x.be)+' to break even</div><ul class="bcw">'+
  x.legs.map(function(l){return '<li><b>'+esc(legNeed(l))+'</b> '+am(l.pr)+' <span class="pcm">(our chance '+pct(l.pc)+')</span></li>'}).join('')+'</ul><p class="sub" style="margin:8px 0 0;font-size:14px">'+esc(x.note)+'</p></div>'}
function parlayHTML(){var X=(D.ODD&&D.ODD.PX)||[];X=X.filter(function(x){return !past(x.t)});if(!X.length)return '';
  return '<h3>Parlays <span class="pcm">for fun, tracked as their own record</span></h3><div class="bgrid">'+X.map(parlayCard).join('')+'</div><p class="sub" style="margin-top:8px">Every leg has to hit. Each leg’s price already includes the sportsbook’s cut, and a parlay stacks those cuts, so even good legs make a long shot. Prices are from the one book shown; check your app before betting.</p>'}
function recLine(x){if(!x)return '';var n=x.w+x.l;return esc(x.w+'-'+x.l+(x.p?'-'+x.p:'')+(n?' ('+Math.round(x.w/n*100)+'%)':'')+' · '+(x.u>=0?'+':'')+x.u.toFixed(1)+' units')}
function recordStrip(){var R=(D.ODD||{}).REC,a=R&&R.all;if(!a||!(a.w+a.l+a.p))return '<div class="rstrip">Our picks are tracked from this week on: each one locks at the last update before kickoff and is graded automatically after the game. <a href="#" data-goto="results">See results</a></div>';
  return '<div class="rstrip"><b>Our record:</b> '+recLine(a)+' <span class="pcm">(1 unit per pick)</span> · <a href="#" data-goto="results">See every pick</a></div>'}
function combos(){var O=D.ODD,C=[],byTeam={};
  O.P.forEach(function(p){if(hurt(p.gid)||past(p.ko))return;var x=pa(p);if(!x)return;var ok=x.td?x.ls>0:(x.o&&(x.o.ls>0||x.o.s>=1)&&x.b.dir>0);if(!ok)return;(byTeam[p.t]=byTeam[p.t]||[]).push(x)});
  Object.keys(byTeam).forEach(function(t){var L=byTeam[t];L.forEach(function(x){if(!/^Pass/.test(x.p.mk))return;L.forEach(function(y){if(y.p.gid===x.p.gid||!(/^Rec|Receptions|Anytime/.test(y.p.mk)))return;
    var lx=x.td?null:x.o.q.pt,ly=y.td?null:y.o.q.pt,hit=function(z,ln,v){return ln==null?v>=1:v>ln},wy={};y.p.v.forEach(function(v){wy[v[0]]=v[2]});
    var n=0,both=0;x.p.v.forEach(function(v){if(wy[v[0]]==null)return;n++;if(hit(x,lx,v[2])&&hit(y,ly,wy[v[0]]))both++});
    if(n>=4&&both/n>=.5)C.push({x:x,y:y,n:n,both:both})})})});
  return C.sort(function(a,b){return b.both/b.n-a.both/a.n||b.n-a.n}).slice(0,6)}
function comboHTML(){var C=combos();if(!C.length)return '';
  return '<h3>Same-game combos <span class="pcm">teammates who tend to hit together</span></h3><div class="bgrid">'+C.map(function(c){var f=function(x){var q=x.td?x.q:x.o.q;return '<b>'+esc(x.p.n)+'</b> '+esc(x.td?'anytime TD':'over '+q.pt+' '+x.p.mk.toLowerCase())+' <span class="pcm">'+am(q.pr)+' '+esc(q.bk)+'</span>'};
    return '<div class="bc l1"><div class="bct" style="font-size:17px">'+esc(c.x.p.t)+' vs '+esc(c.x.p.opp)+'</div><ul class="bcw" style="color:var(--ink)"><li>'+f(c.x)+'</li><li>'+f(c.y)+'</li></ul><div class="bcp"><b>Both hit</b> in '+c.both+' of '+c.n+' games this season</div></div>'}).join('')+'</div><p class="sub" style="margin-top:8px">A QB’s good day usually means his receivers had one too. Books know this, so same-game parlays pay less than the two prices multiplied, and every leg adds the bookmaker’s cut. Check the combined price before betting.</p>'}
function moves(){var M=[];D.ODD.G.forEach(function(g){var m=g.mv||[];if(m.length<2||past(g.t))return;var a=m[0],b=m[m.length-1],ds=(a[1]!=null&&b[1]!=null)?b[1]-a[1]:0,dt=(a[2]!=null&&b[2]!=null)?b[2]-a[2]:0;
  var key=a[1]!=null&&b[1]!=null&&[3,7].some(function(k){return Math.min(Math.abs(a[1]),Math.abs(b[1]))<k&&Math.max(Math.abs(a[1]),Math.abs(b[1]))>k});
  if(Math.abs(ds)>=1||Math.abs(dt)>=1.5||key)M.push({g:g,a:a,b:b,ds:ds,dt:dt,key:key})});return M}
function movesHTML(){var M=moves();var some=D.ODD.G.some(function(g){return (g.mv||[]).length>=2});
  if(!M.length)return '<h3>Line moves</h3><p class="sub">'+(some?'No big moves this week so far.':'We started tracking lines this week; moves show up after a few daily updates.')+'</p>';
  return '<h3>Line moves <span class="pcm">since we first saw each line this week</span></h3><div class="wrap"><table class="olt bt" data-gl="moves"><tr><th>Game</th><th>Spread</th><th>Total</th><th>Note</th></tr>'+M.map(function(m){var g=m.g;
    return '<tr><td>'+esc(g.a)+' at '+esc(g.h)+'</td><td'+heat(m.ds?-m.ds/3:null,1)+'>'+esc(g.h)+' '+spf(m.a[1])+' → '+spf(m.b[1])+'</td><td>'+(m.a[2]!=null?esc(m.a[2])+' → '+esc(m.b[2]):'–')+'</td><td class="wr">'+(m.key?'Crossed a key number (3 or 7). ':'')+(m.ds<=-1?'Money on '+esc(g.h)+'. ':m.ds>=1?'Money on '+esc(g.a)+'. ':'')+(m.dt>=1.5?'Total going up.':m.dt<=-1.5?'Total going down.':'')+'</td></tr>'}).join('')+'</table></div>'}
function closest(){var L=[];D.ODD.G.forEach(function(g){if(past(g.t))return;['hs','as','ov','un','mh','ma'].forEach(function(k){var x=gside(g,k);if(x&&x.v!=null&&!x.flag&&x.v>-.01)L.push({g:g,x:x})})});return L.sort(function(a,b){return b.x.v-a.x.v}).slice(0,3)}
function renderB(){var O=D.ODD;if(!O||!O.G){$('bfr').textContent='';$('bo').innerHTML='<div class="card"><b>Odds aren’t loaded right now.</b> They come back with the next refresh.</div>';return}
  $('bfr').innerHTML='Lines updated '+ago(O.at)+' · props updated '+ago(O.pat)+(O.left!=null?' · '+O.left+' odds credits left':'');
  var cfb=BS.lg==='cfb';if(cfb&&BS.v==='props')BS.v='picks';syncHash();
  [].forEach.call($('blg').children,function(b){b.setAttribute('aria-pressed',b.dataset.l===BS.lg)});$('bv').querySelector('[data-v="props"]').hidden=cfb;$('bselw').hidden=cfb;
  if(cfb&&D.CFB){var nc=META_CFB();$('bfr').innerHTML=nc}
  [].forEach.call($('bv').children,function(b){b.setAttribute('aria-pressed',b.dataset.v===BS.v)});$('bctl').hidden=BS.v!=='props';$('bbk').value=BS.book;
  var bnote=BS.book==='best'?'':'<p class="sub">Showing '+esc(BS.book)+' only. Switch to “Best available” to shop every book.</p>';
  if(BS.lg==='cfb'&&BS.v!=='mine'){var part=BS.v==='games'?'games':BS.v==='results'?'results':'picks';$('bo').innerHTML=part==='results'?cfbResults():collegeView(part);var cc=$('cconf');if(cc)cc.onchange=function(){CBS.conf=this.value;renderB()};var cpo=$('cpo');if(cpo)cpo.onchange=function(){CBS2.po=this.checked;renderB()};var cq=$('cq');if(cq)cq.oninput=function(){CBS.q=this.value;var p=this.selectionStart;renderB();var n=$('cq');n.focus();try{n.setSelectionRange(p,p)}catch(e){}};return}
  if(BS.v==='picks'){var L=pickList(),na=!L;if(na)L=[];var G_=L.filter(function(c){return c.t==='g'}),P_=L.filter(function(c){return c.t==='p'}),top=L[0],mr=O.MR||{};
    if(top){G_=G_.filter(function(c){return c!==top});P_=P_.filter(function(c){return c!==top})}
    var h=bnote+(top?pickCard(top,true):na?'<div class="card">Picks aren’t available in this update. They come back with the next refresh.</div>':'<div class="card">No picks clear the bar right now'+(BS.book==='best'?'':' at '+esc(BS.book))+'. Props usually post Thursday and Friday.</div>');
    h=recordStrip()+h;
    var CL=G_.length?[]:closest();
    h+='<h3>Game lines <span class="pcm">spreads, totals, moneylines</span></h3>'+(G_.length?'<div class="bgrid">'+G_.slice(0,BS.more?30:6).map(function(c){return pickCard(c)}).join('')+'</div>':'<p class="sub">No game line clears the bar right now. That’s normal: spreads and totals are what sportsbooks price most carefully. The closest ones'+(BS.book==='best'?'':' at '+esc(BS.book))+':</p>'+(CL.length?'<ul class="bcw" style="color:var(--ink)">'+CL.map(function(c){return '<li><b>'+esc(gname(c.g,c.x.k,c.x.q))+'</b> '+am(c.x.q.pr)+' '+esc(c.x.q.bk)+' <span class="pcm">('+esc(c.g.a)+' at '+esc(c.g.h)+'; '+(c.x.v>=0?'about '+(c.x.v*100).toFixed(1)+'% better than':'about')+' a fair bet)</span></li>'}).join('')+'</ul>':''));
    h+='<h3>Player props</h3>'+(P_.length?'<div class="bgrid">'+P_.slice(0,BS.more?60:9).map(function(c){return pickCard(c)}).join('')+'</div>':'<p class="sub">No prop picks right now. Yardage props usually post Thursday and Friday.</p>');
    if(!BS.more&&(G_.length>6||P_.length>9))h+='<p><button class="back" id="bmore">Show all '+L.length+' picks</button></p>';
    h+=parlayHTML()+comboHTML()+movesHTML();
    h+='<div class="note"><b>How picks work.</b> We look for two things. <b>A better price:</b> a sportsbook paying more than a fair bet should, measured against Pinnacle, the sharpest sportsbook (with its built-in cut taken out). <b>A lean:</b> for player props, our projection is well past the line and he has beaten that line in most games; for spreads, our team model likes the side by 2.5+ points. One strong signal makes a level II pick; both together make level III. We skip underdogs longer than +250, big favorites shorter than -300, and prices so good they probably mean a book hasn’t updated yet. To come out ahead at the usual -110 price, you need to win about 52.4% of bets. Our spread model is '+(mr.w||0)+'-'+(mr.l||0)+(mr.p?'-'+mr.p:'')+' this season when it disagreed with the closing line by 2.5+ points, which is too few games to trust, so it’s only a second opinion. Its totals record is '+(mr.tw||0)+'-'+(mr.tl||0)+', so we don’t use it for totals.</div>';
    $('bo').innerHTML=h;var mb=$('bmore');if(mb)mb.onclick=function(){BS.more=true;renderB()};return}
  if(BS.v==='results'){$('bo').innerHTML=resultsView();return}
  if(BS.v==='mine'){$('bo').innerHTML=mineView();return}
  if(BS.v==='games'){$('bo').innerHTML=bnote+'<div class="ggrid">'+O.G.map(gameCard).join('')+'</div><p class="sub" style="margin-top:12px">Green cells pay 2.5%+ more than fair odds. Tap + to save a bet to My bets. “model” marks the side our team model likes by 2.5+ points. Matchup edges for each game are under NFL → Matchups.</p>';return}
  var q=BS.q.toLowerCase(),list=O.P.filter(function(p){return (BS.mk==='ALL'||p.mk===BS.mk)&&(BS.gm==='ALL'||p.t===BS.gm||p.opp===BS.gm)&&(!q||p.n.toLowerCase().indexOf(q)>-1)});
  if(BS.lo)list=list.filter(function(p){var x=pa(p);return x&&x.s>=1});
  $('bo').innerHTML=bnote+'<p class="sub">'+list.length+' props, best spots first.<span class="dsk"> Green means the projection or hit rate is over the line, red under; dots are his last games (green over, red under).</span></p>'+propTable(list.slice(0,400),true)}
function initB(){$('pc').addEventListener('click',function(e){toggleBet(e)},true);$('bo').addEventListener('change',function(e){var s=e.target.closest('.stk');if(!s)return;var L=mbLoad();L.forEach(function(b){if(b.id===s.dataset.id)b.stake=s.value});mbSave(L);renderB()});
var MKS=['ALL','Pass yds','Rush yds','Rec yds','Receptions','Pass TDs','Anytime TD'],O=D.ODD;
  $('bmk').innerHTML=MKS.map(function(m){return '<button data-m="'+m+'" aria-pressed="'+(m==='ALL')+'">'+(m==='ALL'?'All':m)+'</button>'}).join('');
  $('bmk').addEventListener('click',function(e){var m=e.target.dataset.m;if(!m)return;BS.mk=m;[].forEach.call($('bmk').children,function(b){b.setAttribute('aria-pressed',b.dataset.m===m)});renderB()});
  $('bgm').innerHTML='<option value="ALL">All games</option>'+(O&&O.G?O.G.map(function(g){return '<option value="'+esc(g.h)+'">'+esc(g.a)+' at '+esc(g.h)+'</option>'}).join(''):'');
  $('bbk').innerHTML='<option value="best">Best available (all books)</option>'+(O&&O.books?O.books.map(function(b){return '<option>'+esc(b)+'</option>'}).join(''):'');
  if(O&&O.books&&BS.book!=='best'&&O.books.indexOf(BS.book)<0)BS.book='best';
  $('bbk').onchange=function(){BS.book=this.value;try{store.set('book',BS.book)}catch(e){}renderB()};
  $('bgm').onchange=function(){BS.gm=this.value;renderB()};$('bq').oninput=function(){BS.q=this.value;renderB()};$('blo').onchange=function(){BS.lo=this.checked;renderB()};
  $('blg').addEventListener('click',function(e){var l=e.target.dataset.l;if(!l)return;BS.lg=l;try{store.set('blg',l)}catch(x){}if(BS.v==='props')BS.v='picks';renderB()});
  $('bv').addEventListener('click',function(e){var v=e.target.dataset.v;if(!v)return;BS.v=v;BS.more=false;renderB()});
  $('bo').addEventListener('click',function(e){var a=e.target.closest('a.pn');if(a){e.preventDefault();openCard(a.dataset.n,a.dataset.t);return}
    if(toggleBet(e))return;
    var dl=e.target.closest('[data-del]');if(dl){mbSave(mbLoad().filter(function(x){return x.id!==dl.dataset.del}));renderB();return}
    var gt=e.target.closest('[data-goto]');if(gt){e.preventDefault();BS.v=gt.dataset.goto;renderB();return}
    var b=e.target.closest('.gprop');if(b){BS.v='props';BS.gm=b.dataset.gm;$('bgm').value=BS.gm;renderB();$('sb').scrollIntoView({behavior:'smooth'})}})}
register({id:'bet',label:'Betting',icon:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 10h3M8 14h8M14 10h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',panels:['sb'],wide:true,dataKeys:['ODD','CFB'],init:initB,
  select:function(v,p){BS.lg=p.lg==='cfb'?'cfb':'nfl';if(v==='college'){BS.lg='cfb';v='picks'}if(v){BS.v=v;BS.more=false}},
  render:renderB,current:function(){return {view:BS.v,params:BS.lg==='cfb'?{lg:'cfb'}:{}}}});
register({id:'picks',parent:'bet',label:'Picks',dataKeys:['ODD'],render:renderB});
register({id:'games',parent:'bet',label:'Games',dataKeys:['ODD'],render:renderB});
register({id:'props',parent:'bet',label:'Props',dataKeys:['ODD'],render:renderB});
