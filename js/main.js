// Boot: draws the nav, loads data/index.json and data/core.json (the part of data.json every view needs at start;
// see "data shards" in registry.js), prepares the shared rows, then runs the init of every section whose data is all
// in core (registration order, each in its own try/catch: guard), and finally applies the address-bar route. Other
// sections load their data and run their init on first visit.
// VER is the build stamp on this script's own URL (build.py writes it into index.html), used to cache-bust the data.
var VER=(function(){var s=document.currentScript,m=s&&/[?&]v=([^&#]*)/.exec(s.src);return m?m[1]:''})();
var HLN={schedule:'this week’s games',injuries:'injuries',rosters:'injured reserve list',depth:'depth charts',weekly:'game-by-game stats',snaps:'snap counts',dynasty:'dynasty values',college_prospects:'college prospects',player_cards:'player cards',odds:'NFL betting lines',odds_by_book:'single-book picks',college_betting:'college betting lines'};
function fresh(){var s=D.META&&D.META.sources;if(D.META&&D.META.built)$('upd').textContent='Updated '+D.META.built.replace(/ at .*/,'');
  var H=(D.META&&D.META.health)||{},bad=Object.keys(H).filter(function(k){return /^failed/.test(H[k])}).map(function(k){return HLN[k]||k.replace(/_/g,' ')});
  if(bad.length){$('hl').innerHTML='Some sections didn’t update today: '+esc(bad.join(', '))+'. They should come back with the next refresh.';$('hl').hidden=false}
  if(!s)return;var x=[];
  if(s.weekly_stats)x.push('Game stats through week '+s.weekly_stats.week);if(s.depth)x.push('depth chart from '+s.depth.asof);if(s.injuries)x.push('injury report from week '+s.injuries.week);
  $('fr').textContent=x.length?x.join(', ')+'.':''}
async function load(){
  D={};
  try{var got=await Promise.all([fetchData('data/index.json'),fetchData('data/core.json')]);setIndex(got[0]);takeShard('core',got[1])}
  catch(err){
    // No data/ yet (index.html restamped before the first split build), or index.json and core.json from two builds
    // (mid-deploy): data.json whole has everything from one build.
    console.warn('Loading data.json whole instead of data/:',err.message);
    try{D=await fetchData('data.json');WHOLE=true}catch(e2){console.error('Couldn’t load the data:',e2);bootFailed();return}}
  // Without the player rows every section would show plausible but wrong numbers, so this one is fatal.
  try{prepRows()}catch(err){console.error('Couldn’t prepare the player rows (P, X, OLP):',err);bootFailed();return}
  guard({label:'Update notes',dataKeys:['META'],init:fresh},'init');
  $('ld').hidden=true;
  bootSections();
  wireNav();wireChrome();
  guard({label:'Glossary and colors',init:function(){initGloss();setColors(COLORS);$('clr').onclick=function(){setColors(!COLORS)}}},'init');
  startRouter();
}
// The page can't start: say so in #ld (under Players) and in the header line, which shows whatever view is open.
function bootFailed(){var m='Couldn’t load the stats data. Check your connection and refresh the page.';$('ld').textContent=m;$('hl').textContent=m;$('hl').hidden=false}
// The offensive rows A (one per player, every position) and the injury/depth/snap fields on D.X and D.OLP rows.
function prepRows(){
  ['QB','RB','WR','TE','K'].forEach(function(p){D.P[p].forEach(function(r){var a=[r[0],r[1],p,r[2]].concat(r[3]);a.pp=a[4];a.sd=r[4];a.inj=r[5];a.dl=r[6];a.fm=r[7];a.gid=r[8];if(r[7]){a.sn=r[7][2];a.sn3=r[7][3]}setForm(a);A.push(a)})});
  D.X.forEach(function(r){r.inj=r[17];r.dl=r[18];if(r[19]){r.sn=r[19][2];r.sn3=r[19][3]}});(D.OLP||[]).forEach(function(r){r.inj=r[7]});
}
// The Display menu on phones, and tap-to-expand notes.
function wireChrome(){
  $('dsp').addEventListener('click',function(e){e.stopPropagation();var o=$('top').classList.toggle('open');this.setAttribute('aria-expanded',o)});
  document.addEventListener('click',function(e){if($('top').classList.contains('open')&&!e.target.closest('#ctl')&&e.target!==$('dsp')){$('top').classList.remove('open');$('dsp').setAttribute('aria-expanded','false')}
    var n=e.target.closest('.note');if(n&&!e.target.closest('a,button,input,select')&&window.matchMedia&&matchMedia('(max-width: 600px)').matches)n.classList.toggle('open')});
}
buildNav();
load();
