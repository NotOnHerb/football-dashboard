// Fantasy -> Rankings (dynasty): value board, diamonds and sleepers, rookie picks. Data: DY.P, DY.K.
// ---------------- Dynasty
var DS={v:'b',f:1,p:'ALL',q:'',c:'val',d:-1};
function dRows(){var V=DS.f===1?7:8,rows=D.DY.P.map(function(r){var o=r.slice();o.val=r[V];o.inj=r[14];o.dl=r[15];return o});
  ['QB','RB','WR','TE'].forEach(function(p){var g=rows.filter(function(r){return r[1]===p});
    g.slice().sort(function(a,b){return b.val-a.val}).forEach(function(r,i){r.vr=i+1});
    g.filter(function(r){return r[10]!=null&&r[9]>=3}).sort(function(a,b){return b[10]-a[10]}).forEach(function(r,i){r.pr=i+1});
    g.forEach(function(r){r.gap=r.pr?r.vr-r.pr:null;r.s3=r[13]!=null&&r[12]!=null?r[13]-r[12]:null;r.f3=r[11]!=null&&r[10]!=null?Math.round((r[11]-r[10])*10)/10:null})});
  return rows}
var DC=[['Player',0,-1],['Pos',1,-1],['Team',2,-1],['Age',3,1],['Drafted','dr',-1],['College',6,-1],['Value','val',0],['Pos rank','vr',0],['PPR/g',10,1],['Prod rank','pr',0],['Value gap','gap',0],['Last 3',11,1],['Snap %',12,0],['Snap % L3',13,0]];
function dCell(c,r){var v=r[c[1]];
  if(c[1]===0)return '<td class="nm">'+v+tags(r)+'</td>';
  if(c[1]===1)return '<td><span class="tag '+v+'">'+v+'</span></td>';
  if(c[1]==='dr')return '<td>'+(r[4]?r[4]+(r[5]?' R'+r[5]:''):'–')+'</td>';
  if(c[1]==='vr'||c[1]==='pr')return '<td>'+(v?r[1]+v:'–')+'</td>';
  if(c[1]==='gap')return '<td>'+(v==null?'–':'<span class="'+(v>=8?'up':v<=-8?'dn':'')+'">'+(v>0?'+':'')+v+'</span>')+'</td>';
  if(c[2]<0)return '<td'+(c[1]===6?' class="wr"':'')+'>'+(v||'–')+'</td>';
  return '<td>'+f(v,c[2])+'</td>'}
function dTbl(cols,rows,extra){return '<table><tr>'+cols.map(function(c){var on=!extra&&c[1]===DS.c;return '<th tabindex="0" data-c="'+c[1]+'" class="'+(on?'on':'')+'">'+c[0]+(on?(DS.d>0?' ▲':' ▼'):'')+'</th>'}).join('')+(extra?'<th>Why</th>':'')+'</tr>'+rows.map(function(r){return '<tr>'+cols.map(function(c){return dCell(c,r)}).join('')+(extra?'<td class="wr">'+extra(r)+'</td>':'')+'</tr>'}).join('')+'</table>'}
function why(r){var w=[];if(r.gap>=8)w.push('Producing like '+r[1]+r.pr+', valued '+r[1]+r.vr);if(r.s3>=8)w.push('Snaps up '+r.s3+' pts lately');if(r.f3>=3)w.push('Last 3 games +'+r.f3+' PPR/g');if(r[3]!=null&&r[3]<=23)w.push('Age '+r[3]);return w.map(function(x){return '<span class="why">'+x+'</span>'}).join(' ')}
function renderD(){var m=false;$('dt').hidden=false;$('dsub').hidden=false;$('dfmt').hidden=DS.v==='c';$('ccl').hidden=DS.v!=='c';if(m){$('dctl').hidden=true;return}
  if(DS.v==='c'){$('dctl').hidden=false;return renderC()}
  if(!D.DY){$('dt').innerHTML='<p class="sub" style="padding:14px">Dynasty values aren’t available right now. They come back with the next refresh.</p>';return}
  $('dctl').hidden=DS.v==='k';var q=DS.q.toLowerCase(),rows=dRows().filter(function(r){return(DS.p==='ALL'||r[1]===DS.p)&&(!q||r[0].toLowerCase().indexOf(q)>-1)});
  if(DS.v==='k'){var K=D.DY.K.slice().sort(function(a,b){return b[DS.f]-a[DS.f]});$('dsub').textContent='Trade value of future rookie draft picks. Early, mid and late mean where in the round the pick is expected to land.';
    $('dt').innerHTML='<table><tr><th>Pick</th><th>Value</th></tr>'+K.map(function(k){return '<tr><td class="nm">'+k[0]+'</td><td>'+k[DS.f].toLocaleString()+'</td></tr>'}).join('')+'</table>'}
  else if(DS.v==='g'){var CUT={QB:24,RB:36,WR:36,TE:18};rows=rows.filter(function(r){return r[3]!=null&&r[3]<=25.5&&r.vr>(r[1]==='TE'||r[1]==='QB'?8:20)&&((r.pr&&r.pr<=CUT[r[1]])||(r[13]!=null&&r[13]>=60))&&(r.gap>=8||r.s3>=8||r.f3>=3)&&!(r.inj&&OUTS[r.inj[0]])});
    rows.sort(function(a,b){var s=function(r){return Math.min(Math.max(r.gap||0,0),30)+Math.max(r.s3||0,0)/2+Math.max(r.f3||0,0)*2};return s(b)-s(a)});
    $('dsub').textContent='Young players (25 or under, outside the top tier at their position) whose usage or production is running ahead of their trade value. Buy-low candidates before the market catches up. To make the list a player has to be producing (top 36 RB or WR, top 24 QB, top 18 TE by PPR per game) or playing at least 60% of snaps over his last 3 games. Sorted by how far ahead of his value he’s running.';
    $('dt').innerHTML=rows.length?dTbl(DC.filter(function(c){return c[1]!==6}),rows.slice(0,60),why):'<p class="sub" style="padding:14px">No players match right now.</p>'}
  else{rows=sortRows(rows,DS.c,DS.d);$('dsub').textContent='Every fantasy-relevant player with a dynasty trade value. Value gap compares where he ranks in production (PPR per game, 3+ games) with where he ranks in value at his position: a big plus means producing above his price.';
    $('dt').innerHTML=dTbl(DC,rows)}
  $('dnote').textContent='Trade values from DynastyProcess (based on FantasyPros expert rankings), updated '+((D.META.sources.dynasty_values||{}).asof||'')+'. 1QB and Superflex values differ mostly for quarterbacks. Production and snap share are 2026 so far. Rookies and backups with little playing time have no production rank yet.'}
function initD(){
  $('dpos').innerHTML=['ALL','QB','RB','WR','TE'].map(function(p){return '<button data-p="'+p+'" aria-pressed="'+(p==='ALL')+'">'+(p==='ALL'?'All':p)+'</button>'}).join('');
  var grp=function(id,attr,fn){$(id).addEventListener('click',function(e){var v=e.target.dataset[attr];if(v==null)return;[].forEach.call($(id).children,function(b){b.setAttribute('aria-pressed',b.dataset[attr]===v)});fn(v);renderD()})};
  grp('dv','x',function(v){DS.v=v});grp('dfmt','f',function(v){DS.f=+v});grp('dpos','p',function(v){DS.p=v});
  $('dq').oninput=function(){DS.q=this.value;renderD()};
  $('dt').addEventListener('click',function(e){var th=e.target.closest('th');if(!th||th.dataset.c==null)return;var c=ck(th);if(DS.c===c)DS.d*=-1;else{DS.c=c;DS.d=(c==='vr'||c==='pr'||c===3||c===0||c===2)?1:-1}renderD()});
}
register({id:'r',parent:'fan',label:'Rankings',dataKeys:['DY'],init:initD,render:renderD});
