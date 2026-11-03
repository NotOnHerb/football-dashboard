// NFL -> Matchups: trenches (line units, man by man) and skill positions for each game. Data: G, T, X, DEP, ALW.
function ord(n){var v=n%100,x=['th','st','nd','rd'];return n+(x[(v-20)%10]||x[v]||'th')}
function mr(l,a){var k=ix(l),t=D.T.filter(function(r){return r[0]===a})[0];return {v:f(t[k+1],D.TC[k][1]),r:rank(k,t)}}
var LVL=[[18,'III','Big edge'],[10,'II','Clear edge'],[4,'I','Slight edge']];
function meter(lab,o,d,offR,defR){
  var x=(offR[0]+offR[1])/2,y=(defR[0]+defR[1])/2,z=y-x,az=Math.abs(z),lv=null;
  for(var i=0;i<LVL.length;i++)if(az>=LVL[i][0]){lv=LVL[i];break}
  var side=z>0?'o':'d',who=z>0?o+' offense':d+' defense',w=Math.min(az/31,1)*50;
  var txt=lv?'<span class="lvl '+side+'">'+lv[1]+'</span><b>'+lv[2]+': '+who+'</b>':'<span class="lvl e">=</span><b>Even</b>';
  return '<div class="edge">'+lab+': '+txt+'</div><div class="meter" role="img" aria-label="'+lab+': '+(lv?lv[2]+' to '+who:'even')+'"><i class="'+(z>0?'mo':'md')+'" style="'+(z>0?'right':'left')+':50%;width:'+w.toFixed(1)+'%"></i></div><div class="mlab"><span>'+o+' offense avg rank '+x.toFixed(0)+'</span><span>'+d+' defense avg rank '+y.toFixed(0)+'</span></div>';
}
var ACR={'4-3':{LT:['RDE'],LG:['RDT'],C:['RDT','LDT'],RG:['LDT'],RT:['LDE']},'3-4':{LT:['WLB','RDE'],LG:['RDE'],C:['NT'],RG:['LDE'],RT:['SLB','LDE']}};
var THR=['','Low','Solid','High','Elite'];
function olTable(o,d){
  if(!D.DEP||!D.DEP.T[o]||!D.DEP.T[d])return '<p class="sub">Depth charts aren’t available right now, so individual matchups are hidden.</p>';
  var O=D.DEP.T[o],F=D.DEP.T[d],fr={};F.fr.forEach(function(x){fr[x[0]]=x});
  var h='<div class="wrap"><table class="olt"><tr><th>Spot</th><th>'+o+' starter</th><th>Flags</th><th>Likely across from him ('+d+' '+F.s+')</th><th>Threat</th></tr>';
  O.ol.forEach(function(l){
    var opp=(ACR[F.s][l[0]]||[]).map(function(s){return fr[s]}).filter(Boolean);
    var top=opp.reduce(function(m,x){return !m||x[5]>m[5]?x:m},null);
    h+='<tr><td>'+l[0]+'</td><td class="nm">'+l[1]+'</td><td>'+l[2]+(l[3]?' ('+l[3]+' yds)':'')+'</td><td class="wr">'+(opp.length?opp.map(function(x){return '<b>'+x[1]+'</b> ('+x[0]+') · '+x[2]+' sk, '+x[3]+' hits, '+x[4]+' TFL'}).join('<br>'):'–')+'</td><td>'+(top?'<span class="thr t'+top[5]+'">'+THR[top[5]]+'</span>':'–')+'</td></tr>';
  });
  return h+'</table></div>';
}
function side(o,d){
  var P=[['Sack % allowed','Sacks'],['Pass EPA/dropback','QB hits'],['Yds/carry','Tackles for loss'],['Rush EPA/carry','DL tackles for loss']],R=[];
  var h='<h3>'+o+' offense vs '+d+' defense</h3><div class="wrap"><table data-gl="mup"><tr><th>'+o+' offense</th><th>Value</th><th>Rank</th><th>'+d+' defense</th><th>Value</th><th>Rank</th></tr>';
  P.forEach(function(p){var x=mr(p[0],o),y=mr(p[1],d);R.push([x.r,y.r]);h+='<tr><td>'+p[0]+'</td><td>'+x.v+'</td><td>'+ord(x.r)+'</td><td>'+p[1]+'</td><td>'+y.v+'</td><td>'+ord(y.r)+'</td></tr>'});
  h+='</table></div>'+meter('Pass protection vs pass rush',o,d,[R[0][0],R[1][0]],[R[0][1],R[1][1]])+meter('Run game vs front',o,d,[R[2][0],R[3][0]],[R[2][1],R[3][1]])+meter('Overall in the trenches',o,d,[(R[0][0]+R[2][0])/2,(R[1][0]+R[3][0])/2],[(R[0][1]+R[2][1])/2,(R[1][1]+R[3][1])/2]);
  var thr=D.X.filter(function(r){return r[1]===d}).sort(function(x,y){return (y[8]+y[9])-(x[8]+x[9])||y[7]-x[7]}).slice(0,3);
  h+='<h3>'+d+'’s 3 biggest pass-rush threats</h3><p class="sub">'+(thr.length?thr.map(function(r,i){return (i+1)+'. <b>'+r[0]+'</b> ('+r[2]+') · '+r[8]+(r[8]===1?' sack, ':' sacks, ')+r[9]+' QB hits, '+r[7]+' TFL'}).join('<br>'):'No data')+'</p>';
  return h+'<h3>'+o+' line, man by man</h3>'+olTable(o,d);
}
var NOG='<p class="sub">This week’s games aren’t available right now. They come back with the next refresh.</p>';
function matchup(){var g=D.G[+$('gm').value||0];if(!g){$('mu').innerHTML=$('ms').innerHTML=NOG;return}$('mu').innerHTML=side(g[0],g[1])+side(g[1],g[0]);skillRender()}
var SKN={QB:1,RB:2,WR:3,TE:1};
function sp(v){return st.sc==='std'?v[1]:st.sc==='half'?(v[0]+v[1])/2:v[0]}
function srank(t,side,p){var W=D.ALW.T,ks=side==='a'?'aa':side,me=W[t]&&W[t][ks]&&W[t][ks][p];side=ks;if(!me)return null;var x=sp(me),n=0;for(var k in W){var o=W[k][side][p];if(o&&(side==='s'?sp(o)>x:sp(o)<x))n++}return n+1}
function edgeChip(z){var az=Math.abs(z);for(var i=0;i<LVL.length;i++)if(az>=LVL[i][0])return '<span class="lvl '+(z>0?'o':'d')+'" title="'+LVL[i][2]+'">'+LVL[i][1]+'</span>'+(z>0?'Offense':'Defense');return '<span class="lvl e">=</span>Even'}
function skillSide(o,d){
  var W=D.ALW.T;if(!W[o]||!W[d])return '<p class="sub">No game data for this team yet.</p>';
  var h='<h3>'+o+' skill players vs '+d+' defense</h3><div class="wrap"><table class="olt"><tr><th>Pos</th><th>'+o+' players ('+SCL[st.sc]+')</th><th>'+o+' pts/g at spot</th><th>'+d+' allows/g (adj. rank)</th><th>Yds allowed/g</th><th>TD allowed/g</th><th>Edge</th></tr>',ox=[],dy=[],OUT=[];
  ['QB','RB','WR','TE'].forEach(function(p){
    var DK=D.DEP&&D.DEP.T[o]&&D.DEP.T[o].sk&&D.DEP.T[o].sk[p],pl;
    if(DK&&DK.length){var cv=function(x){var v=st.sc==='std'?x[2]:st.sc==='half'&&x[1]!=null?Math.round((x[1]+x[2])*5)/10:x[1];var a=[x[0],o,p,0,v];a.inj=x[3];return a},isOut=function(x){return x[3]&&OUTS[x[3][0]]};
      DK.slice(0,SKN[p]).forEach(function(x,i){if(isOut(x))OUT.push([p,p+(i+1),cv(x)])});
      pl=DK.filter(function(x){return !isOut(x)}).slice(0,SKN[p]).map(cv)}
    else pl=A.filter(function(r){return r[1]===o&&r[2]===p}).sort(function(x,y){return y[7]*y[3]-x[7]*x[3]}).slice(0,SKN[p]);
    var so=W[o].s[p],al=W[d].a[p],ro=srank(o,'s',p),rd=srank(d,'a',p);
    if(!so||!al)return;ox.push(ro);dy.push(rd);
    h+='<tr><td><span class="tag '+p+'">'+p+'</span></td><td class="wr">'+(pl.length?pl.map(function(r){return '<b>'+r[0]+'</b> '+f(r[4],1)+injTag(r.inj)}).join('<br>'):'–')+'</td><td>'+f(sp(so),1)+' ('+ord(ro)+')</td><td>'+f(sp(al),1)+' ('+ord(rd)+')</td><td>'+f(al[2],0)+'</td><td>'+f(al[3],1)+'</td><td>'+edgeChip(rd-ro)+'</td></tr>';
  });
  h+='</table></div>';
  if(OUT.length)h+='<h3>'+o+' starters who are out</h3><p class="sub">These players are listed as starters on the depth chart but are Out on the latest injury report or on injured reserve, so the next man up from the depth chart is shown above. Their numbers are here if they end up playing.</p><div class="wrap"><table class="olt"><tr><th>Pos</th><th>Depth spot</th><th>Player ('+SCL[st.sc]+')</th></tr>'+OUT.map(function(x){return '<tr><td><span class="tag '+x[0]+'">'+x[0]+'</span></td><td>'+x[1]+'</td><td class="nm">'+x[2][0]+' '+f(x[2][4],1)+injTag(x[2].inj)+'</td></tr>'}).join('')+'</table></div>';
  if(ox.length)h+=meter('Overall skill-position matchup',o,d,[ox.reduce(function(a,b){return a+b},0)/ox.length,ox.reduce(function(a,b){return a+b},0)/ox.length],[dy.reduce(function(a,b){return a+b},0)/dy.length,dy.reduce(function(a,b){return a+b},0)/dy.length]);
  var F=D.DEP&&D.DEP.T[d];
  if(F&&F.db&&F.db.length){h+='<h3>'+d+' secondary (starters)</h3><div class="wrap"><table class="olt"><tr><th>Spot</th><th>Player</th><th>INT</th><th>Passes defended</th><th>Tackles</th></tr>'+F.db.map(function(x){return '<tr><td>'+x[0]+'</td><td class="nm">'+x[1]+'</td><td>'+x[2]+'</td><td>'+x[3]+'</td><td>'+x[4]+'</td></tr>'}).join('')+'</table></div>'}
  return h;
}
function skillRender(){
  if(!D.ALW){$('ms').innerHTML='<p class="sub">Game-by-game stats aren’t available right now, so skill matchups are hidden. They come back with the next refresh.</p>';return}
  var g=D.G[+$('gm').value||0];if(!g){$('ms').innerHTML=NOG;return}
  $('ms').innerHTML=skillSide(g[0],g[1])+skillSide(g[1],g[0])+'<div class="note">How it works: “pts/g at spot” is the fantasy points per game this offense gets from that position, ranked 1st (most) to 32nd. “Allows/g” is the fantasy points per game this defense gives up to that position, ranked 1st (toughest, fewest allowed) to 32nd (softest). The edge compares those two ranks with the same levels as the trenches: Even under 4 spots, I (slight) 4 to 9, II (clear) 10 to 17, III (big) 18 or more. Through week '+D.ALW.wk+'. Points follow the PPR, Half PPR or Standard setting on the Players tab. Players shown are the current starters from the latest depth chart (top QB, two RBs, three WRs, top TE). Anyone Out on the latest injury report or on injured reserve moves to the out section and the next man up takes his spot; Questionable and Doubtful players stay in with a tag. A dash means no stats yet this season. Defense ranks are adjusted for schedule: each game counts what the defense allowed compared with what that offense usually scores at the position, so a defense that faced weak offenses doesn’t look tougher than it is. The allows/g number itself is the plain average. A guide, not a prediction.</div>';
}
function initN(){
  $('gm').innerHTML=D.G.map(function(g,i){return '<option value="'+i+'">'+g[0]+' at '+g[1]+' · '+g[2]+'</option>'}).join('');
  $('gm').onchange=matchup;
  $('mv').addEventListener('click',function(e){var m=e.target.dataset.m;if(!m)return;st.mv=m;[].forEach.call($('mv').children,function(x){x.setAttribute('aria-pressed',x.dataset.m===m)});$('mt').hidden=m!=='t';$('ms').hidden=m!=='s'});
  teamTbl('ou');teamTbl('du');matchup();
}
