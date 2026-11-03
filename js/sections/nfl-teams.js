// NFL -> Teams: the team table, one team's detail page and the play-mix bar. Also tab(), which switches the NFL
// views. Data: T, TC, N.
function inV(k){return st.tv==='W'||D.TC[k][4].indexOf(st.tv)>-1}
function rank(k,t){var x=t[k+1],hi=D.TC[k][2];if(x==null)return null;return 1+D.T.filter(function(r){return hi?r[k+1]>x:r[k+1]<x}).length}
function team(a){tab('t');
  var t=D.T.filter(function(r){return r[0]===a})[0],n=D.T.length,g='';
  var out='<button class="back" id="bk">Back to teams</button><h2>'+esc(a)+' '+esc(D.N[a])+'</h2><p class="sub">'+esc(t[1])+' games played. Rank 1 is best in the league (fewest for giveaways, penalties and sacks allowed). Play mix stats are ranked most to least.</p>'+mixBar(t)+'<div class="wrap"><table><tr><th>Stat</th><th>Value</th><th>Rank</th></tr>';
  D.TC.forEach(function(s,k){if(k===0||!inV(k))return;if(s[3]!==g){g=s[3];out+='<tr class="grp"><td colspan="3">'+esc(g)+'</td></tr>'}out+='<tr><td>'+esc(s[0])+'</td><td>'+f(t[k+1],s[1])+'</td><td>'+(rank(k,t)==null?'–':rank(k,t)+' of '+n)+'</td></tr>'});
  out+='</table></div>';
  if(st.tv==='W'||st.tv==='O')['QB','RB','WR','TE'].forEach(function(p){
    var rs=A.filter(function(r){return r[1]===a&&r[2]===p}).sort(function(x,y){return y[7]*y[3]-x[7]*x[3]});
    if(rs.length)out+='<h3>'+p+'s, in order of usage</h3><div class="wrap">'+tbl(colsFor(p,1),rs,-1,1)+'</div>';
  });
  $('td').innerHTML=out;$('td').hidden=false;$('tt').hidden=true;window.scrollTo(0,0);
  $('bk').onclick=function(){$('td').hidden=true;$('tt').hidden=false};
}
function tab(v){st.v=v;[].forEach.call($('tabs').children,function(b){b.setAttribute('aria-pressed',b.dataset.v===v)});$('vp').hidden=v!=='p';$('vt').hidden=v!=='t';$('vn').hidden=v!=='n';$('vc').hidden=v!=='c';syncHash()}
function ix(l){for(var k=0;k<D.TC.length;k++)if(D.TC[k][0]===l)return k}
var TS={tt:[1,-1,0],ou:[null,1,['Sack % allowed','Pass EPA/dropback','Yds/carry','Rush EPA/carry','OL penalties','OL penalty yds']],du:[null,-1,['Sacks','QB hits','Tackles for loss','DL sacks','DL QB hits','DL tackles for loss']]};
function mixBar(t){if(st.tv!=='W'&&st.tv!=='O')return '';var k=ix('Pass rate % (approx)'),p=t[k+1];if(p==null)return '';
  var lg=D.T.reduce(function(a,r){return a+(r[k+1]||0)},0)/D.T.length,pa=t[ix('Pass att/g')+1],ra=t[ix('Rush att/g')+1];
  return '<h3>Play mix</h3><div class="mix" role="img" aria-label="Pass '+p+' percent, run '+(100-p)+' percent. League average pass rate '+lg.toFixed(0)+' percent"><span class="p" style="flex:'+p+'">Pass '+p+'%</span><span class="r" style="flex:'+(100-p)+'">Run '+(100-p)+'%</span><i style="left:'+lg.toFixed(1)+'%"></i></div><p class="sub">'+f(pa,1)+' pass attempts and '+f(ra,1)+' rush attempts per game. The black line is the league average pass rate ('+lg.toFixed(0)+'%). Sacks count as pass plays and QB scrambles count as runs, so this is approximate.</p>'}
function teamTbl(id){
  var s=TS[id],idx=s[2]?s[2].map(ix):D.TC.map(function(t,k){return k}).filter(function(k){return id!=='tt'||inV(k)});
  if(s[0]==null)s[0]=idx[0]+1;
  if(id==='tt'&&idx.map(function(k){return k+1}).concat([0]).indexOf(s[0])<0){s[0]=idx[1]+1;s[1]=D.TC[idx[1]][2]?-1:1}
  var cols=[['Team',0]].concat(idx.map(function(k){return [D.TC[k][0],k+1,D.TC[k][1]]}));
  $(id).innerHTML='<table><tr>'+cols.map(function(c){var on=c[1]===s[0];return '<th tabindex="0" data-c="'+esc(c[1])+'" class="'+(on?'on':'')+'">'+esc(c[0])+(on?(s[1]>0?' ▲':' ▼'):'')+'</th>'}).join('')+'</tr>'+sortRows(D.T,s[0],s[1]).map(function(r){return '<tr class="go" tabindex="0" data-t="'+esc(r[0])+'"><td class="nm">'+esc(r[0])+' '+esc(D.N[r[0]])+'</td>'+cols.slice(1).map(function(c){return '<td>'+f(r[c[1]],c[2])+'</td>'}).join('')+'</tr>'}).join('')+'</table>';
}
function renderT(){teamTbl('tt')}
register({id:'nfl',label:'NFL',icon:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19c-1-6 3-13 14-14-1 11-8 15-14 14z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M9 15l6-6M10 11l3 3M12 9l3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',panels:['nflnav','vp','vt','vn','vc'],dataKeys:[],
  select:function(v){if(v)st.v=v},render:function(){tab(st.v)},current:function(){return {view:st.v}}});
register({id:'t',parent:'nfl',label:'Teams',dataKeys:['T','TC','N'],init:renderT,render:renderT});
