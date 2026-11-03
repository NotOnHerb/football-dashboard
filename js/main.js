// Boot: loads data.json, prepares the shared rows and starts every section.
// VER is the build stamp on this script's own URL (build.py writes it into index.html), used to cache-bust data.json.
var VER=(function(){var s=document.currentScript,m=s&&/[?&]v=([^&#]*)/.exec(s.src);return m?m[1]:''})();
var HLN={schedule:'this week’s games',injuries:'injuries',rosters:'injured reserve list',depth:'depth charts',weekly:'game-by-game stats',snaps:'snap counts',dynasty:'dynasty values',college_prospects:'college prospects',player_cards:'player cards',odds:'NFL betting lines',college_betting:'college betting lines'};
function fresh(){var s=D.META&&D.META.sources;if(D.META&&D.META.built)$('upd').textContent='Updated '+D.META.built.replace(/ at .*/,'');
  var H=(D.META&&D.META.health)||{},bad=Object.keys(H).filter(function(k){return /^failed/.test(H[k])}).map(function(k){return HLN[k]||k.replace(/_/g,' ')});
  if(bad.length){$('hl').innerHTML='Some sections didn’t update today: '+esc(bad.join(', '))+'. They should come back with the next refresh.';$('hl').hidden=false}
  if(!s)return;var x=[];
  if(s.weekly_stats)x.push('Game stats through week '+s.weekly_stats.week);if(s.depth)x.push('depth chart from '+s.depth.asof);if(s.injuries)x.push('injury report from week '+s.injuries.week);
  $('fr').textContent=x.length?x.join(', ')+'.':''}
async function load(){
  try{
    var res=await fetch('data.json?v='+VER,{cache:'no-cache'});
    if(!res.ok)throw new Error(res.status);
    D=await res.json();
  }catch(err){$('ld').textContent='Couldn’t load the stats data. Check your connection and refresh the page.';return}
  ['QB','RB','WR','TE','K'].forEach(function(p){D.P[p].forEach(function(r){var a=[r[0],r[1],p,r[2]].concat(r[3]);a.pp=a[4];a.sd=r[4];a.inj=r[5];a.dl=r[6];a.fm=r[7];a.gid=r[8];if(r[7]){a.sn=r[7][2];a.sn3=r[7][3]}setForm(a);A.push(a)})});
  D.X.forEach(function(r){r.inj=r[17];r.dl=r[18];if(r[19]){r.sn=r[19][2];r.sn3=r[19][3]}});(D.OLP||[]).forEach(function(r){r.inj=r[7]});
  fresh();
  $('ld').hidden=true;wire();renderP();renderT();initN();cInit();initX();initD();initC();initF();initGloss();initFM();initCards();initB();setColors(COLORS);$('clr').onclick=function(){setColors(!COLORS)};
}
load();
