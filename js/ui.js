// Cross-cutting table helpers: the row table (tbl, cell, tags), column sorting (sortRows, sortClick, reSort),
// glossary tooltips (gloss) and heat colors on stat cells (colorize). gloss, reSort and colorize run after every
// render through the MutationObserver set up in initGloss.
function sortRows(rows,c,dir){return rows.slice().sort(function(a,b){var x=a[c],y=b[c];if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return(typeof x==='string'?x.localeCompare(y):x-y)*dir})}
var OUTS={Out:1,IR:1,Reserve:1};
function injTag(j){return j?' <span class="thr '+(OUTS[j[0]]?'t4':'t3')+'" title="'+(j[1]||'Injury')+', week '+j[2]+' report">'+j[0]+' · wk '+j[2]+'</span>':''}
function tags(r){return (r.dl?' <span class="dl'+(r.dl[1]?' on':'')+'" title="'+(r.dl[1]?'Starter':'Backup')+' on the latest depth chart">'+r.dl[0]+'</span>':'')+injTag(r.inj)}
function cell(c,r){var v=r[c[1]];
  if(c[2]<0){if(c[1]===2)return '<td style="text-align:right"><span class="tag '+v+'">'+v+'</span></td>';if(c[1]===0)return '<td class="nm">'+v+tags(r)+'</td>';return '<td>'+v+'</td>'}
  if(c[1]==='tr')return '<td>'+(v==null?'–':'<span class="'+(v>=1?'up':v<=-1?'dn':'')+'">'+(v>0?'▲ +':v<0?'▼ ':'')+v.toFixed(1)+'</span>')+'</td>';
  return '<td>'+f(v,c[2])+'</td>'}
function tbl(cols,rows,sc,sd){
  return '<table><tr>'+cols.map(function(c){var on=c[1]===sc;return '<th tabindex="0" data-c="'+c[1]+'" class="'+(on?'on':'')+'">'+c[0]+(on?(sd>0?' ▲':' ▼'):'')+'</th>'}).join('')+'</tr>'+rows.map(function(r){return '<tr>'+cols.map(function(c){return cell(c,r)}).join('')+'</tr>'}).join('')+'</table>';
}
function ck(th){var c=th.dataset.c;return isNaN(c)?c:+c}
function sortClick(e,k,fn){var th=e.target.closest('th');if(!th||th.dataset.c==null)return;var c=ck(th);
  if(st[k+'c']===c)st[k+'d']*=-1;else{st[k+'c']=c;st[k+'d']=(k==='p'?c<=2:c===0)?1:-1}fn()}
function glFor(t,el){var cx=el&&el.closest&&el.closest('[data-gl]');if(cx){var g=GLC[cx.getAttribute('data-gl')];if(g&&g[t])return g[t]}if(GL[t])return GL[t];for(var i=0;i<GLR.length;i++)if(GLR[i][0].test(t))return GLR[i][1];return null}
var glTip,glT;
function gloss(){document.querySelectorAll('td.nm:not([tabindex])').forEach(function(el){if(!el.closest('tr.go'))el.setAttribute('tabindex','0')});document.querySelectorAll('th:not([data-g]),td:not([data-g])').forEach(function(el){el.setAttribute('data-g','');var t=el.textContent.replace(/[▲▼]/g,'').trim();if(el.tagName==='TD'&&(t.length<4||el.children.length))return;var d=el.dataset.tip||glFor(t,el);if(d){el.setAttribute('aria-label',t+': '+d);el.dataset.tip=d;el.classList.add('gl')}})}
// ---------------- colored stat cells
var COLORS=(function(){try{return localStorage.getItem('colors')!=='off'}catch(e){return true}})();
var LOWB=['INT','Sack %','Fum lost','Fumbles lost','Giveaways','Penalties','Penalty yds','Penalties/g','Penalty yds/g','Sack % allowed','OL penalties','OL penalty yds','FG missed','Missed','Missed 40+','Punts blocked against','Kicks blocked against','Flags','Interceptions thrown','Consensus','Avg rank','Pos rank','Prod rank','Recruit rank','Rank','Week rank','#'];
var NEUT=['GP','Age','Team games','Pass att/g','Rush att/g','Dropbacks/g','Pass rate % (approx)','Run rate % (approx)','Pass yds share %','Pass TD share %','Drafted','Class','Ht / Wt','Long','Long FG','Spot','Starting spot','Depth spot','Record','Points for','Players','Picks','Vs yours','Season ','Snap % L3 ','Att','Car','Rec','Pick','Range','Boards'];
function cnum(s){s=s.replace(/[▲▼,×%+]/g,'').replace('−','-').trim();var m=s.match(/^(-?\d+(?:\.\d+)?)(?:st|nd|rd|th)?(?: of \d+)?$/);return m?parseFloat(m[1]):null}
function colorize(){document.querySelectorAll('main table').forEach(function(tb){
  if(tb.classList.contains('bt')||tb.dataset.cz===(COLORS?'1':'0'))return;tb.dataset.cz=COLORS?'1':'0';
  var rows=[].slice.call(tb.rows);if(rows.length<6)return;var hdr=[].slice.call(rows[0].cells).map(function(c){return c.textContent.replace(/[▲▼]/g,'').trim()});
  var statTable=hdr.indexOf('Stat')>-1,boards=(D&&D.CF&&D.CF.CB)?D.CF.CB.S.map(function(s){return s[0]}):[];
  hdr.forEach(function(h,ci){if(ci===0)return;var cells=rows.slice(1).map(function(r){return r.cells[ci]}).filter(Boolean);
    cells.forEach(function(c){c.style.background=''});if(!COLORS)return;
    if(NEUT.indexOf(h)>-1||(statTable&&h!=='Rank')||/^(Team|Player|Pos|School|Conf|College|Owner|Opponent|Verdict|Grade|Why|Now|Status|Edge|Threat|Matchup)$/.test(h))return;
    var low=LOWB.indexOf(h)>-1||/rank/i.test(h)||boards.indexOf(h)>-1;
    var vals=cells.map(function(c){return c.colSpan>1?null:cnum(c.textContent)}),nums=vals.filter(function(v){return v!=null}).sort(function(a,b){return a-b});
    if(nums.length<5||nums[0]===nums[nums.length-1])return;
    cells.forEach(function(c,i){var v=vals[i];if(v==null)return;var lo=0,hi=0;for(var k=0;k<nums.length;k++){if(nums[k]<v)lo++;else if(nums[k]===v)hi++}
      var p=(lo+hi/2)/nums.length;if(low)p=1-p;var d=(p-.5)*2;if(Math.abs(d)<.3)return;
      var a=Math.round((Math.abs(d)-.3)/.7*30+6);c.style.background='color-mix(in srgb,'+(d>0?'#2e9e5b':'#d9534f')+' '+a+'%,var(--panel))'})})})}
var SORTS={};
function sortVal(c){if(!c)return null;if(c.dataset.v!=null)return +c.dataset.v;var t=c.textContent.replace(/[▲▼]/g,'').trim();if(!t||t==='–')return null;
  var m=t.match(/^(\d+) of (\d+)/);if(m)return +m[1]/Math.max(1,+m[2]);m=t.match(/^(III|II|I)\b/);if(m)return m[1].length;
  m=t.replace(/,/g,'').replace('−','-').match(/^([+-])?\$?(\d+(?:\.\d+)?)/);if(m)return (m[1]==='-'?-1:1)*parseFloat(m[2]);return t.toLowerCase()}
function tblSig(tb){return [].map.call(tb.rows[0].cells,function(c){return c.textContent.replace(/[▲▼]/g,'').trim()}).join('|')}
function sortable(tb){return tb.rows.length>2&&!tb.classList.contains('gmt')&&!tb.querySelector('th[data-c]')&&![].some.call(tb.rows,function(r){return r.classList.contains('grp')||r.cells.length!==tb.rows[0].cells.length})}
function applySort(tb,ci,dir){var rows=[].slice.call(tb.rows,1),body=rows[0].parentNode;
  rows.sort(function(a,b){var x=sortVal(a.cells[ci]),y=sortVal(b.cells[ci]);if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;if(typeof x==='number'&&typeof y==='number')return (x-y)*dir;return String(x).localeCompare(String(y))*dir});
  rows.forEach(function(r){body.appendChild(r)});tb.dataset.sorted='1';
  [].forEach.call(tb.rows[0].cells,function(c,i){var ar=c.querySelector('.sar');if(ar)ar.remove();c.classList.toggle('on',i===ci);if(i===ci)c.insertAdjacentHTML('beforeend','<span class="sar">'+(dir>0?' ▲':' ▼')+'</span>')})}
function reSort(){document.querySelectorAll('main table:not([data-sorted]), #pc table:not([data-sorted])').forEach(function(tb){if(!tb.rows.length)return;var s=SORTS[tblSig(tb)];if(s&&sortable(tb))applySort(tb,s[0],s[1])})}
document.addEventListener('click',function(e){var th=e.target.closest('th');if(!th||th.dataset.c!=null)return;var tb=th.closest('table');if(!tb||th.parentNode!==tb.rows[0]||!sortable(tb))return;
  var ci=[].indexOf.call(th.parentNode.cells,th),sig=tblSig(tb),cur=SORTS[sig],first=sortVal(tb.rows[1].cells[ci]);
  var dir=cur&&cur[0]===ci?-cur[1]:(typeof first==='number'?-1:1);SORTS[sig]=[ci,dir];applySort(tb,ci,dir)});
function setColors(on){COLORS=on;try{localStorage.setItem('colors',on?'on':'off')}catch(e){}var b=$('clr');if(b)b.textContent=on?'Colors on':'Colors off';document.querySelectorAll('main table').forEach(function(tb){delete tb.dataset.cz});colorize()}
function initGloss(){glTip=document.createElement('div');glTip.className='tip';glTip.hidden=true;document.body.appendChild(glTip);
  new MutationObserver(function(){clearTimeout(glT);glT=setTimeout(function(){gloss();reSort();colorize()},30)}).observe(document.querySelector('main'),{childList:true,subtree:true});gloss();
  document.addEventListener('mouseover',function(e){var el=e.target.closest('.gl');if(!el){glTip.hidden=true;return}glTip.textContent=el.dataset.tip;glTip.hidden=false;var r=el.getBoundingClientRect(),w=Math.min(300,innerWidth-24);glTip.style.maxWidth=w+'px';var x=Math.max(12,Math.min(r.left,innerWidth-w-12));glTip.style.left=x+'px';glTip.style.top=(r.bottom+window.scrollY+6)+'px'});
  document.addEventListener('scroll',function(){glTip.hidden=true},{passive:true});
  var keys=Object.keys(GL).sort(function(a,b){return a.localeCompare(b)});$('glist').innerHTML=keys.map(function(k){return '<dt>'+k+'</dt><dd>'+GL[k]+'</dd>'}).join('')}
