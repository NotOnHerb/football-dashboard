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
// store: localStorage under one namespace ("fd:"). The page used to save its 12 settings under bare keys; on first
// use every bare key that is still there is moved under the namespace, so no saved setting or bet is lost.
// Every call is safe when storage is blocked (private mode): reads give null, writes are dropped.
var store=(function(){var NS='fd:',OLD=['blg','book','colors','espn_league','espn_team','fmt','last_league','motion','mybets','scene','sleeper_user','theme'],moved=false;
  function ls(){try{return window.localStorage}catch(e){return null}}
  function migrate(s){if(moved)return;moved=true;OLD.forEach(function(k){try{var v=s.getItem(k);if(v==null)return;if(s.getItem(NS+k)==null)s.setItem(NS+k,v);s.removeItem(k)}catch(e){}})}
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
