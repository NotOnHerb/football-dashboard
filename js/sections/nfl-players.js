// NFL -> Players: offense (renderP), defense (renderX) and offensive linemen (renderOL), plus the scoring
// switch setSc that re-renders every view showing fantasy points. Data: P, PC, X, OLP.
function colsFor(p,noTeam){
  var c=[['Player',0,-1]];
  if(p==='ALL')c.push(['Pos',2,-1]);
  if(!noTeam)c.push(['Team',1,-1]);
  c.push(['GP',3,0]);
  (p==='ALL'?D.PC.WR.slice(0,5):D.PC[p]).forEach(function(s,k){c.push([s[0],4+k,s[1]]);if(k===0&&p!=='K'){c.push(['Last 3','l3',1],['Trend','tr',1],['Snap %','sn',0],['Snap % L3','sn3',0])}});
  if(p!=='ALL')c=c.filter(function(x){return (typeof x[1]==='number'&&x[1]<4)||A.some(function(r){return r[2]===p&&r[x[1]]!=null})});
  return c;
}
function renderP(){
  var cols=colsFor(st.pos),q=st.q.toLowerCase();
  if(!cols.some(function(c){return c[1]===st.pc}))st.pc=4;
  var rows=A.filter(function(r){return(st.pos==='ALL'||r[2]===st.pos)&&(st.tm==='ALL'||r[1]===st.tm)&&r[7]*r[3]>=st.mn&&(!q||r[0].toLowerCase().indexOf(q)>-1)});
  rows=sortRows(rows,st.pc,st.pd);
  $('pt').innerHTML=rows.length?tbl(cols,rows,st.pc,st.pd):'<p class="sub" style="padding:14px">No players match. Try clearing the search or filters.</p>';
}
function wire(){
  $('pt').addEventListener('click',function(e){var th=e.target.closest('th');if(!th)return;var c=ck(th);
    if(st.side==='D'){if(DX.c===c)DX.d*=-1;else{DX.c=c;DX.d=c<=2?1:-1}renderX()}
    else if(st.pos==='OL'){if(OS.c===c)OS.d*=-1;else{OS.c=c;OS.d=c<=2||c===4?1:-1}renderOL()}
    else sortClick(e,'p',renderP)});
  $('side').addEventListener('click',function(e){var d=e.target.dataset.d;if(!d)return;st.side=d;[].forEach.call($('side').children,function(x){x.setAttribute('aria-pressed',x.dataset.d===d)});$('pos').hidden=d==='D';$('xg').hidden=d!=='D';$('sc').hidden=d==='D';$('mn').hidden=d==='D'||st.pos==='OL'||st.pos==='K';render()});
  ['tt','ou','du'].forEach(function(id){$(id).addEventListener('click',function(e){var tr=e.target.closest('tr[data-t]');if(tr)return team(tr.dataset.t);var th=e.target.closest('th');if(!th)return;var c=+th.dataset.c,s=TS[id];if(s[0]===c)s[1]*=-1;else{s[0]=c;s[1]=c===0?1:-1}teamTbl(id)});$(id).addEventListener('keydown',function(e){if(e.key==='Enter'){var tr=e.target.closest('tr[data-t]');if(tr)team(tr.dataset.t)}})});
  $('tabs').addEventListener('click',function(e){var v=e.target.dataset.v;if(v)tab(v)});
  $('tv').addEventListener('click',function(e){var w=e.target.dataset.w;if(!w)return;st.tv=w;[].forEach.call($('tv').children,function(x){x.setAttribute('aria-pressed',x.dataset.w===w)});renderT();if(!$('td').hidden){var h=$('td').querySelector('h2');if(h)team(h.textContent.split(' ')[0])}});
  $('mn').onchange=function(){st.mn=+this.value;render()};
  $('sc').addEventListener('click',function(e){var s=e.target.dataset.s;if(s)setSc(s)});
  $('pos').innerHTML=['ALL','QB','RB','WR','TE','OL','K'].map(function(p){return '<button data-p="'+p+'" aria-pressed="'+(p==='ALL')+'">'+(p==='ALL'?'All':p)+'</button>'}).join('');
  $('pos').addEventListener('click',function(e){var p=e.target.dataset.p;if(!p)return;st.pos=p;[].forEach.call($('pos').children,function(b){b.setAttribute('aria-pressed',b.dataset.p===p)});$('mn').hidden=p==='OL'||p==='K';$('sc').hidden=p==='OL'||p==='K';render()});
  $('tm').innerHTML='<option value="ALL">All teams</option>'+Object.keys(D.N).sort().map(function(t){return '<option value="'+t+'">'+t+' '+D.N[t]+'</option>'}).join('');
  $('tm').onchange=function(){st.tm=this.value;render()};
  $('q').oninput=function(){st.q=this.value;render()};
}
var TB={xx:{c:3,d:-1,k:'OL',cols:[['Player',0,-1],['Team',1,-1],['Pos',2,-1],['Penalties',3,0],['Penalty yds',4,0],['Fumbles lost',5,0]]}};
function renderTB(id){var s=TB[id],rows=D[s.k];$(id).innerHTML=rows.length?tbl(s.cols,sortRows(rows,s.c,s.d),s.c,s.d):'<p class="sub" style="padding:14px">No linemen match that search.</p>'}
var DX={g:'ALL',c:15,d:-1,q:'',t:'ALL'};
var XC=[['Player',0,-1],['Team',1,-1],['Pos',2,-1],['GP',3,0],['Tackles',4,0],['Solo',5,0],['Tkl/g',6,1],['TFL',7,0],['Sacks',8,1],['QB hits',9,0],['INT',10,0],['PD',11,0],['FF',12,0],['Fum rec',13,0],['Def TD',14,0]];XC.splice(4,0,['IDP/g',16,1],['IDP pts',15,1],['Snap %','sn',0],['Snap % L3','sn3',0]);
var KC=[['Player',0,-1],['Team',1,-1],['GP',3,0],['FG made',4,0],['FG att',5,0],['FG %',6,1],['Long',7,0],['0-39',8,0],['40-49',9,0],['50+',10,0],['Missed',11,0],['Missed 40+',12,0],['XP made',13,0],['XP att',14,0],['Fantasy pts',15,0],['Pts/g',16,1]];
var XG={DL:['DE','DT','NT','DL'],LB:['LB','ILB','MLB','OLB'],CB:['CB'],S:['S','SAF','FS','SS','DB']};
function renderX(){
  var k=false,cols=XC,q=st.q.toLowerCase();
  if(!cols.some(function(c){return c[1]===DX.c}))DX.c=15;
  var rows=(k?D.K:D.X).filter(function(r){return(k||DX.g==='ALL'||XG[DX.g].indexOf(r[2])>-1)&&(st.tm==='ALL'||r[1]===st.tm)&&(!q||r[0].toLowerCase().indexOf(q)>-1)});
  $('pt').innerHTML=rows.length?tbl(cols,sortRows(rows,DX.c,DX.d),DX.c,DX.d):'<p class="sub" style="padding:14px">No players match. Try clearing the search or filters.</p>';
}
function initX(){
  $('xg').innerHTML=['ALL','DL','LB','CB','S'].map(function(g){return '<button data-g="'+g+'" aria-pressed="'+(g==='ALL')+'">'+(g==='ALL'?'All':g)+'</button>'}).join('');
  $('xg').addEventListener('click',function(e){var g=e.target.dataset.g;if(!g)return;DX.g=g;[].forEach.call($('xg').children,function(b){b.setAttribute('aria-pressed',b.dataset.g===g)});renderX()});
}
var OS={c:4,d:1},OLC=[['Player',0,-1],['Team',1,-1],['Pos',2,-1],['GP',3,0],['Starting spot',4,-1],['Penalties',5,0],['Penalty yds',6,0]];
function renderOL(){var q=st.q.toLowerCase(),rows=(D.OLP||[]).filter(function(r){return(st.tm==='ALL'||r[1]===st.tm)&&(!q||r[0].toLowerCase().indexOf(q)>-1)});
  var srt=OS.c===4?rows.slice().sort(function(a,b){var o=['LT','LG','C','RG','RT'],x=o.indexOf(a[4]),y=o.indexOf(b[4]);x=x<0?9:x;y=y<0?9:y;return((x===9)-(y===9))*OS.d||a[1].localeCompare(b[1])||(x-y)}):sortRows(rows,OS.c,OS.d);
  $('pt').innerHTML=rows.length?tbl(OLC,srt,OS.c,OS.d):'<p class="sub" style="padding:14px">No linemen match. Try clearing the search or team filter.</p>'}
function render(){if(st.side==='D')renderX();else if(st.pos==='OL')renderOL();else renderP()}
var SCL={ppr:'PPR/g',half:'Half PPR/g',std:'Std/g'};
function setForm(r){var fm=r.fm;if(!fm)return;r.l3=fm[0]==null?null:st.sc==='ppr'?fm[0]:st.sc==='std'?fm[1]:Math.round((fm[0]+fm[1])*5)/10;r.tr=r.l3==null||r[4]==null?null:Math.round((r.l3-r[4])*10)/10}
function setSc(m){st.sc=m;A.forEach(function(r){r[4]=m==='ppr'?r.pp:m==='std'?r.sd:Math.round((r.pp+r.sd)*5)/10;setForm(r)});[].forEach.call($('fsc').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===m)});[].forEach.call($('csc').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===m)});if(st.sec==='fan'&&FV==='c')renderD();['QB','RB','WR','TE'].forEach(function(p){D.PC[p][0][0]=SCL[m]});[].forEach.call($('sc').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===m)});render();if(CP.a)cRender();if(D.G)skillRender();if(st.sec==='fan'&&FV==='s')renderF();if(st.sec==='fan'&&FV==='m'&&RL.M)leagueRender()}
register({id:'p',parent:'nfl',label:'Players',dataKeys:['P','PC','X','OLP'],init:function(){wire();renderP();initX()},render:render});
