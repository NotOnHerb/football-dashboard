// Shared state and helpers every other script uses: the dataset D, the offensive player rows A, the NFL tab
// state st, $ (getElementById), f (number formatting), esc and html (HTML escaping), store (saved settings)
// and F (a row field by name).
var D,A=[];
var $=function(i){return document.getElementById(i)};
var st={sec:'nfl',v:'t',pos:'ALL',tm:'ALL',q:'',pc:4,pd:-1,tc:1,td:-1,mn:0,dq:'',tv:'W',side:'O',sc:'ppr',mv:'t'};
function f(v,d){return v==null?'–':v.toFixed(d)}

// ---------------- escaping
// Raw marks a string as markup that is already safe (built by html`` or wrapped with raw()).
function Raw(s){this.s=s}
Raw.prototype.toString=function(){return this.s};
function raw(s){return s instanceof Raw?s:new Raw(String(s==null?'':s))}
// esc: text -> HTML-safe text (a Raw passes through unchanged).
function esc(s){if(s instanceof Raw)return s.s;return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
// html`<b>${name}</b>`: escapes every interpolated value unless it is a Raw; arrays are joined. Returns a Raw, so
// templates nest, and it turns into a plain string wherever a string is expected (innerHTML, +).
function html(parts){var out=parts[0];for(var i=1;i<arguments.length;i++){var v=arguments[i];out+=(Array.isArray(v)?v.map(esc).join(''):esc(v))+parts[i]}return new Raw(out)}
// safeUrl: the URL itself when it is http(s), else null (keeps javascript: and the like out of href).
function safeUrl(u){u=String(u==null?'':u).trim();return /^https?:\/\//i.test(u)?u:null}

// ---------------- saved settings
// store: localStorage under one namespace ("fd:"). The page used to save its 12 settings under bare keys. On each
// load (first store call) they are copied in, never removed: the site shares its origin (notonherb.github.io) with
// other pages that may use the same generic names, and an old tab or a rolled-back page still writes them.
//   - a setting is copied only when its fd: copy is absent (a value saved by this page wins);
//   - saved bets: when the bare "mybets" differs from the last one merged (fd:mybets.bare), its bets are merged into
//     fd:mybets by id: bets missing from fd:mybets are added at the end, fd:mybets' own version of a bet is kept,
//     nothing is dropped. A bet removed here stays removed unless the bare list changes again.
// fd:migrated records when the first copy ran. Every call is safe when storage is blocked (private mode): reads give
// null, writes are dropped.
var store=(function(){var NS='fd:',OLD=['blg','book','colors','espn_league','espn_team','fmt','last_league','motion','mybets','scene','sleeper_user','theme'],moved=false;
  function ls(){try{return window.localStorage}catch(e){return null}}
  function list(v){try{var x=JSON.parse(v||'[]');return Array.isArray(x)?x:[]}catch(e){return []}}
  function mergeBets(s){var bare=s.getItem('mybets');if(bare==null||bare===s.getItem(NS+'mybets.bare'))return;
    var mine=s.getItem(NS+'mybets');
    if(mine==null)s.setItem(NS+'mybets',bare);
    else{var L=list(mine),ids={};L.forEach(function(b){if(b&&b.id!=null)ids[b.id]=1});
      list(bare).forEach(function(b){if(b&&b.id!=null&&!ids[b.id]){ids[b.id]=1;L.push(b)}});s.setItem(NS+'mybets',JSON.stringify(L))}
    s.setItem(NS+'mybets.bare',bare)}
  function migrate(s){if(moved)return;moved=true;
    OLD.forEach(function(k){if(k==='mybets')return;try{var v=s.getItem(k);if(v!=null&&s.getItem(NS+k)==null)s.setItem(NS+k,v)}catch(e){}});
    try{mergeBets(s)}catch(e){}
    try{if(s.getItem(NS+'migrated')==null)s.setItem(NS+'migrated',new Date().toISOString())}catch(e){}}
  function get(k){var s=ls();if(!s)return null;migrate(s);try{return s.getItem(NS+k)}catch(e){return null}}
  function set(k,v){var s=ls();if(!s)return;migrate(s);try{s.setItem(NS+k,v)}catch(e){}}
  return {get:get,set:set,NS:NS,OLD:OLD}})();

// ---------------- named fields
// F(block,row,name): the value of field `name` in a positional row of data.json block `block` (e.g. F('DY.P',r,'age')),
// using the field lists build.py exports as D.SCHEMA. Throws on an unknown block or field, so a renamed field fails loudly.
var F_IX={};
function F(block,row,name){var k=block+'\n'+name,i=F_IX[k];
  if(i==null){var s=D&&D.SCHEMA&&D.SCHEMA[block];if(!s)throw new Error('No schema for block '+block);i=s.indexOf(name);if(i<0)throw new Error('No field '+name+' in '+block);F_IX[k]=i}
  return row[i]}
