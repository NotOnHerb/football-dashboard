// Shared state and helpers every other script uses: the dataset D, the offensive player rows A, the NFL tab
// state st, $ (getElementById), f (number formatting) and esc (HTML escaping).
var D,A=[];
var $=function(i){return document.getElementById(i)};
var st={sec:'nfl',v:'t',pos:'ALL',tm:'ALL',q:'',pc:4,pd:-1,tc:1,td:-1,mn:0,dq:'',tv:'W',side:'O',sc:'ppr',mv:'t'};
function f(v,d){return v==null?'–':v.toFixed(d)}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
