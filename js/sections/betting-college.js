// Betting -> College: college picks, game cards and results. Data: CFB.
var CBS={conf:'ALL',q:''};
var CBS2={po:false};
function cfFav(g,v){return v==null?null:(v<=0?{t:g.h,pt:v}:{t:g.a,pt:-v})}
function cfLine(g,v){var f=cfFav(g,v);return f==null?'–':f.pt===0?'Even':f.t+' '+f.pt}
function cfBest(g){var B=g.books,hs=null,as=null,mh=null,ma=null,ov=null,un=null;
  Object.keys(B).forEach(function(bn){var v=B[bn];if(bn==='Pinnacle')return;
    if(v[0]!=null){var hp=v[5]!=null?v[5]:null,ap=v[6]!=null?v[6]:null;
      if(!hs||v[0]>hs.pt||(v[0]===hs.pt&&(hp||-110)>(hs.pr||-110)))hs={pt:v[0],pr:hp,bk:bn};
      if(!as||-v[0]>as.pt||(-v[0]===as.pt&&(ap||-110)>(as.pr||-110)))as={pt:-v[0],pr:ap,bk:bn}}
    if(v[1]!=null){if(!ov||v[1]<ov.pt)ov={pt:v[1],bk:bn};if(!un||v[1]>un.pt)un={pt:v[1],bk:bn}}
    if(v[2]!=null&&(!mh||v[2]>mh.pr))mh={pr:v[2],bk:bn};if(v[3]!=null&&(!ma||v[3]>ma.pr))ma={pr:v[3],bk:bn}});
  return {hs:hs,as:as,mh:mh,ma:ma,ov:ov,un:un}}
function cfSide(t,q){return q?'<b>'+t+' '+spf(q.pt)+'</b>'+(q.pr!=null?' '+am(q.pr):'')+' <small class="pcm">'+q.bk+'</small>':'–'}
function cfPickCard(x){var C=D.CFB,bt=C.BT||{},g=(C.G||[]).filter(function(y){return y.id===x.gid})[0]||{},t_=x.sd==='hs'?x.h:x.a,rec=x.s>=2?(bt.l2||bt.record):(bt.l1||bt.record);
  var L=x.lines||{},ladder=Object.keys(L).sort(function(a,b){return L[b]-L[a]}).map(function(bn){var me=bn===x.bk;return '<span class="lad'+(me?' on':'')+'">'+bn+' <b>'+spf(L[bn])+'</b></span>'}).join('');
  var wp=g.wp!=null?(x.sd==='hs'?g.wp:1-g.wp):null;
  return '<div class="bc l'+x.s+'"><div class="bch">'+lvl(x.s)+'<span class="bct">'+t_+' '+spf(x.pt)+'</span></div><div class="bcp"><b>'+am(x.pr)+'</b> '+x.bk+' · '+x.a+(g.neutral?' vs ':' at ')+x.h+' · '+kick(x.t)+'</div>'+
    '<ul class="bcw"><li><b>What you need:</b> '+needTxt({a:x.a,h:x.h},x.sd,{pt:x.pt})+'.</li><li><b>Better number:</b> '+x.bk+' gives '+t_+' '+spf(x.pt)+'; the other books sit at '+spf(x.others)+'. That '+x.gap+'-point gap is the edge.</li>'+
    (wp!=null?'<li><b>Win chance from the odds:</b> '+t_+' about '+Math.round(wp*100)+'% to win outright.</li>':'')+
    '<li><b>This rule’s record:</b> '+rec[0]+'-'+rec[1]+' ('+Math.round(rec[0]/(rec[0]+rec[1])*100)+'%) for '+(x.s>=2?'1.5 to 3':'1 to 1.5')+'-point gaps, 2023-25.</li></ul><div class="ladr">'+ladder+'</div></div>'}
function cfGameCard(g,pk){var b=cfBest(g),fav=cfFav(g,g.sp),n=Object.keys(g.books).length,wp=g.wp;
  var tags_=[];if(g.ac)tags_.push(g.ac);if(g.hc&&g.hc!==g.ac)tags_.push(g.hc);if(g.neutral)tags_.push('Neutral site');
  var ml=g.mod==null?null:(Math.abs(g.mod)<0.5?'even':(g.mod>0?g.h+' by '+g.mod.toFixed(1):g.a+' by '+(-g.mod).toFixed(1)));
  return '<div class="gc'+(pk?' cpk':'')+'"><div class="gch"><div><div class="gt" style="font-size:22px">'+g.a+' <small>'+(g.neutral?'vs':'at')+'</small> '+g.h+'</div><div class="pcm">'+tags_.join(' · ')+'</div></div>'+(pk?'<span class="pill2">Pick: '+(pk.sd==='hs'?pk.h:pk.a)+' '+spf(pk.pt)+' '+pk.bk+'</span>':'')+'</div>'+
   (n?'<div class="wrap"><table class="bt gmt" data-gl="cfbc"><tr><th></th><th>'+g.a+'</th><th>'+g.h+'</th></tr><tr><td>Spread</td><td>'+cfSide(g.a,b.as)+'</td><td>'+cfSide(g.h,b.hs)+'</td></tr><tr><td>Total</td><td>'+(b.ov?'O '+b.ov.pt+' <small class="pcm">'+b.ov.bk+'</small>':'–')+'</td><td>'+(b.un?'U '+b.un.pt+' <small class="pcm">'+b.un.bk+'</small>':'–')+'</td></tr><tr><td>Moneyline</td><td>'+(b.ma?'<b>'+am(b.ma.pr)+'</b> <small class="pcm">'+b.ma.bk+'</small>':'–')+'</td><td>'+(b.mh?'<b>'+am(b.mh.pr)+'</b> <small class="pcm">'+b.mh.bk+'</small>':'–')+'</td></tr></table></div>':'<p class="sub" style="margin:0">Lines not posted yet.</p>')+
   (wp!=null?'<div class="wpb" style="max-width:none"><span style="width:'+Math.round((1-wp)*100)+'%" class="wa">'+g.a+' '+Math.round((1-wp)*100)+'%</span><span style="width:'+Math.round(wp*100)+'%" class="wh">'+Math.round(wp*100)+'% '+g.h+'</span></div>':'')+
   '<div class="gmeta">'+(fav?'<span><b>Sportsbooks:</b> '+cfLine(g,g.sp)+(g.ou!=null?', total '+g.ou:'')+' (middle of '+n+' books)</span>':'')+(ml?'<span><b>Our ratings:</b> '+ml+' <span class="pcm">(context only)</span></span>':'')+'</div>'+
   (n>1?'<details><summary class="pcm" style="cursor:pointer">Every book’s spread</summary><div class="ladr">'+Object.keys(g.books).filter(function(bn){return g.books[bn][0]!=null}).map(function(bn){return '<span class="lad'+(pk&&pk.bk===bn?' on':'')+'">'+bn+' <b>'+cfLine(g,g.books[bn][0])+'</b></span>'}).join('')+'</div></details>':'')+'</div>'}
function collegeView(part){var C=D.CFB;if(!C)return '<div class="card">College lines aren’t loaded right now. They come back with the next refresh.</div>';
  var R=C.REC||{w:0,l:0,p:0,u:0},bt=C.BT||{},G=C.G.filter(function(g){return !past(g.t)}),picks=(C.PK||[]).filter(function(x){return !past(x.t)}).sort(function(a,b){return b.s-a.s||b.gap-a.gap});
  if(part==='picks'){var h='<div class="rstrip"><b>College record:</b> '+R.w+'-'+R.l+(R.p?'-'+R.p:'')+' · '+(R.u>=0?'+':'')+R.u.toFixed(1)+' units <span class="pcm">· '+G.length+' games on the board · '+picks.length+' pick'+(picks.length===1?'':'s')+'</span></div>';
    h+=picks.length?'<div class="bgrid">'+picks.map(cfPickCard).join('')+'</div>':'<div class="card"><b>No college picks right now.</b> A pick needs one sportsbook to be 1 to 3 points off the others on a game. Extra books arrive Friday and Saturday mornings, which is when most picks show up.</div>';
    return h+'<div class="note"><b>How college picks work.</b> We bet one thing in college: a better number. When at least three sportsbooks have a game and one of them is 1 to 3 points off the others, we take that book’s number. From 2023 to 2025, 1.5 to 3-point gaps won '+bt.l2[0]+'-'+bt.l2[1]+' (level II) and 1 to 1.5-point gaps won '+bt.l1[0]+'-'+bt.l1[1]+' (level I), one bet per game. Our own college ratings have been about a coin flip against closing lines, so they never make picks. Check the number in your app first: if that book has moved to match the others, the edge is gone.</div>'}
  var confs={};G.forEach(function(g){if(g.hc)confs[g.hc]=1;if(g.ac)confs[g.ac]=1});
  var BP4=['SEC','Big Ten','Big 12','ACC'],p4=function(g){return BP4.indexOf(g.hc)>-1||BP4.indexOf(g.ac)>-1},q=CBS.q.toLowerCase(),pk={};picks.forEach(function(x){pk[x.gid]=x});
  var rows=G.filter(function(g){return (CBS.conf==='ALL'||(CBS.conf==='P4'?p4(g):g.hc===CBS.conf||g.ac===CBS.conf))&&(!q||(g.a+' '+g.h).toLowerCase().indexOf(q)>-1)&&(!CBS2.po||pk[g.id])});
  rows.sort(function(a,b){return (a.t<b.t?-1:a.t>b.t?1:0)||(p4(b)-p4(a))});
  var h='<div class="bar"><select id="cconf" aria-label="Conference"><option value="ALL">All conferences</option><option value="P4"'+(CBS.conf==='P4'?' selected':'')+'>Power 4 games</option>'+Object.keys(confs).sort().map(function(c){return '<option'+(c===CBS.conf?' selected':'')+'>'+c+'</option>'}).join('')+'</select><input id="cq" type="search" placeholder="Search teams" aria-label="Search teams" value="'+CBS.q.replace(/"/g,'&quot;')+'"><label class="sub" style="display:flex;gap:6px;align-items:center;margin:0"><input type="checkbox" id="cpo" style="flex:0;min-width:0"'+(CBS2.po?' checked':'')+'> Picks only</label></div>';
  if(!rows.length)return h+'<p class="sub">No games match.</p>';
  var slot=null;rows.forEach(function(g){var s=new Date(g.t).toLocaleString(undefined,{weekday:'long',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
    if(s!==slot){if(slot)h+='</div>';h+='<h3>'+s+'</h3><div class="ggrid">';slot=s}h+=cfGameCard(g,pk[g.id])});
  return h+'</div><p class="sub" style="margin-top:12px">Best line and price for each side across the books we track (Pinnacle is left out because US bettors can’t use it). Lines from CollegeFootballData each morning, plus more books on Friday and Saturday mornings.</p>'}
function cfbResults(){var C=D.CFB;if(!C)return '<div class="card">College results aren’t loaded right now.</div>';var R=C.REC||{w:0,l:0,p:0,u:0},L=C.LG||[];
  var h='<div class="tiles"><div class="tile"><b>'+R.w+'-'+R.l+(R.p?'-'+R.p:'')+'</b><span>College picks · '+(R.u>=0?'+':'')+R.u.toFixed(1)+' units</span></div></div>';
  if(!L.length)return h+'<p class="sub">No college picks logged yet. They lock at kickoff and grade after the game.</p>';
  return h+'<div class="wrap"><table class="olt bt" data-gl="res"><tr><th>Week</th><th>Pick</th><th>Price</th><th>Result</th><th>Units</th></tr>'+L.map(function(r){var t_=r.sd==='hs'?r.h:r.a;return '<tr><td>'+r.wk+'</td><td class="wr">'+t_+' '+spf(r.pt)+' ('+r.a+' at '+r.h+')'+(r.fin?' <small class="pcm">final '+r.fin[0]+'-'+r.fin[1]+'</small>':'')+'</td><td><b>'+am(r.pr)+'</b> <small class="pcm">'+r.bk+'</small></td><td>'+(r.res?resChip(r.res):past(r.t)?'<span class="rs o">Locked</span>':'<span class="rs o">Open</span>')+'</td><td>'+(r.res?((r.u>=0?'+':'')+r.u.toFixed(2)):'–')+'</td></tr>'}).join('')+'</table></div>'}
function META_CFB(){var s=(D.META.sources||{}).odds_college||{};return 'College lines updated '+ago((D.CFB.at||'').length===16?D.CFB.at+'Z':D.CFB.at)+(s.at?' · extra books '+ago(s.at):'')+(D.ODD&&D.ODD.left!=null?' · '+D.ODD.left+' odds credits left':'')}
