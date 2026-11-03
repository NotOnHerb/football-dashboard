// The betting pick engine, as the page runs it: prices, fair odds, value, prop chances and the pick list.
// Moved unchanged from template.html; build.py has its own copy (engine/). Data: ODD.
var MINL={'Pass yds':150,'Rush yds':25,'Rec yds':25,'Receptions':2.5,'Pass TDs':.5};
var AG=null;function ag(gid){if(!AG){AG={};A.forEach(function(a){if(a.gid)AG[a.gid]=a})}return AG[gid]||{}}
function hurt(gid){var a=ag(gid);return a.inj&&(OUTS[a.inj[0]]||a.inj[0]==='Doubtful')}
function i2p(a){return a>0?100/(a+100):-a/(-a+100)}
function dec(a){return a>0?1+a/100:1-100/a}
function RU(){return (D.ODD&&D.ODD.RU)||{val:[.025,.045,.07],stale:.1,mlmax:250,mlmin:-300,model:2.5,pick:2,minl:MINL,tdmax:300}}
function valS(v){var r=RU().val;return v==null?0:v>=r[2]?3:v>=r[1]?2:v>=r[0]?1:0}
function past(iso){return iso&&new Date(iso)<=new Date()}
// ---- game sides
var GS={hs:['s',0,1],as:['s',2,3],ov:['o',0,1],un:['o',0,2],mh:['m',-1,0],ma:['m',-1,1]};
function gq(g,k){var m=GS[k],best=null;Object.keys(g.b).forEach(function(bn){if(BS.book!=='best'&&bn!==BS.book)return;var x=g.b[bn][m[0]];if(!x||x[m[2]]==null)return;
  var q={pt:m[1]<0?null:x[m[1]],pr:x[m[2]],bk:bn};
  if(!best)best=q;else if(q.pt!=null&&q.pt!==best.pt){if((k==='ov'?best.pt-q.pt:q.pt-best.pt)>0)best=q}else if(q.pr>best.pr)best=q});return best}
function gfair(g,k){var f=g.fair||{};if(k==='hs'||k==='as'){if(!f.s||f.s[1]==null)return null;return {pt:k==='hs'?f.s[0]:-f.s[0],p:k==='hs'?f.s[1]:1-f.s[1],sp:1}}
  if(k==='ov'||k==='un'){if(!f.o||f.o[1]==null)return null;return {pt:f.o[0],p:k==='ov'?f.o[1]:1-f.o[1],ov:k==='ov'}}
  return f.m==null?null:{pt:null,p:k==='mh'?f.m:1-f.m}}
// expected value of a price against the market's fair (no-vig) chance; a better number than the market moves the chance about 2% per half point (more across 3 and 7)
function gev(q,fr){if(!q||!fr)return null;var p=fr.p;
  if(fr.pt!=null&&q.pt!==fr.pt){var d=fr.ov?fr.pt-q.pt:q.pt-fr.pt;if(Math.abs(d)>2)return null;
    var step=fr.sp?.02:.015;p+=d/.5*step;if(fr.sp){var lo=Math.min(Math.abs(q.pt),Math.abs(fr.pt)),hi=Math.max(Math.abs(q.pt),Math.abs(fr.pt));if(lo<3&&hi>3||lo<7&&hi>7)p+=(d>0?1:-1)*.03}}
  return p*dec(q.pr)-1}
function gside(g,k){var q=gq(g,k);if(!q)return null;var v=gev(q,gfair(g,k)),me=null,ms=0,vs=valS(v),flag=null,R=RU();
  if(v!=null&&v>R.stale){vs=0;flag='stale'}
  if(k[0]==='m'&&(q.pr>R.mlmax||q.pr<R.mlmin)){vs=0;flag=flag||'range'}
  if(g.mod&&(k==='hs'||k==='as')){me=(k==='hs'?g.mod.m:-g.mod.m)+q.pt;ms=me>=R.model?1:0}
  return {k:k,q:q,v:v,vs:vs,me:me,ms:ms,s:vs+ms,flag:flag}}
function gmk(k){return k[0]==='m'?'ml':(k==='ov'||k==='un')?'total':'spread'}
// ---- props
function pq(p,sd){var best=null;Object.keys(p.b).forEach(function(bn){if(BS.book!=='best'&&bn!==BS.book)return;var x=p.b[bn],q=sd==='u'?{pt:x[2],pr:x[3],bk:bn}:{pt:x[0],pr:x[1],bk:bn};if(q.pr==null||(sd!=='y'&&q.pt==null))return;
  if(!best)best=q;else if(q.pt!==best.pt){if(sd==='u'?q.pt>best.pt:q.pt<best.pt)best=q}else if(q.pr>best.pr)best=q});return best}
function pOver(mk,mu,L){var q=D.ODD.MQ&&D.ODD.MQ[mk];if(!q||!(mu>0))return null;var x=L/mu,c=0;for(var i=0;i<q.length;i++)if(q[i]>x)c++;return Math.min(.99,Math.max(.01,c/q.length+((D.ODD.MC||{})[mk]||0)))}
function ptier(e){return e>=.10?3:e>=.07?2:e>=.04?1:0}
function pa(p){var td=p.mk==='Anytime TD',n=p.v.length,o={p:p,td:td,n:n},MB=D.ODD.MB==null?.5:D.ODD.MB;
  if(td){var q=pq(p,'y');if(!q)return null;var im=i2p(q.pr),pf=p.fair?p.fair[1]:null,P=(p.pj==null||pf==null)?null:MB*p.pj+(1-MB)*pf;
    o.q=q;o.im=im;o.P=P;o.pf=pf;o.d=P==null?null:P-im;o.hits=p.v.filter(function(v){return v[2]>=1}).length;
    o.ls=(P!=null&&n>=4&&q.pr<=RU().tdmax)?ptier(P-im):0;o.b={q:q,ls:o.ls,vs:0,s:Math.min(o.ls,2),dir:1,e:o.d||0,P:P};o.s=o.b.s;return o}
  function side(q,dir){if(!q)return null;var po=pOver(p.mk,p.pj,q.pt),fo=null;
    if(p.fair&&p.fair[0]===q.pt)fo=p.fair[1];else{var pr=Object.keys(p.b).map(function(k){return p.b[k]}).filter(function(x){return x[0]===q.pt&&x[2]===q.pt&&x[1]!=null&&x[3]!=null});if(pr.length){var a=i2p(pr[0][1]),b2=i2p(pr[0][3]);fo=a/(a+b2)}}
    var P=null;if(po!=null&&fo!=null){P=MB*po+(1-MB)*fo;if(dir<0)P=1-P}
    var e=P==null?null:P-i2p(q.pr),h=p.v.filter(function(v){return dir>0?v[2]>q.pt:v[2]<q.pt}).length/n;
    var ls=(e!=null&&n>=4&&q.pt>=(RU().minl[p.mk]||0))?ptier(e):0;
    var v=p.fair&&p.fair[0]===q.pt?(dir>0?p.fair[1]:1-p.fair[1])*dec(q.pr)-1:null,vs=valS(v);if(v!=null&&v>RU().stale)vs=0;if(e!=null&&e<0)vs=0;
    return {q:q,P:P,po:dir>0?po:(po==null?null:1-po),fo:dir>0?fo:(fo==null?null:1-fo),e:e||0,h:h,ls:ls,v:v,vs:vs,s:Math.min(ls,2)+vs,dir:dir}}
  var qo=pq(p,'o'),qu=pq(p,'u');if(!qo&&!qu)return null;o.o=side(qo,1);o.u=side(qu,-1);
  o.b=(o.o&&o.u)?((o.u.s>o.o.s||(o.u.s===o.o.s&&o.u.e>o.o.e))?o.u:o.o):(o.o||o.u);o.s=o.b.s;o.line=(qo||qu).pt;return o}
// ---- picks
function gameOf(team){return (D.ODD.G.filter(function(g){return g.a===team||g.h===team})[0])}
function picks(){var O=D.ODD,L=[];
  O.G.forEach(function(g){if(past(g.t))return;[['hs','as'],['ov','un'],['mh','ma']].forEach(function(pr){var a=gside(g,pr[0]),b=gside(g,pr[1]),x=a&&b?(b.s>a.s?b:a):(a||b);if(x&&x.s>=RU().pick)L.push({t:'g',g:g,x:x,s:x.s,sort:x.s+(x.v||0)*5})})});
  O.P.forEach(function(p){if(hurt(p.gid)||past(p.ko))return;var x=pa(p);if(x&&x.s>=RU().pick)L.push({t:'p',p:p,x:x,s:x.s,sort:x.s+(x.b.e||0)+(x.b.v||0)*5})});
  return L.sort(function(a,b){return b.sort-a.sort})}
