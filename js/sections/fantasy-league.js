// Fantasy -> My league: loads a Sleeper or ESPN league and shows dynasty power rankings and advice (sRender),
// or redraft standings, lineup and waivers (fRender); the trade finder. Also the Fantasy layout (FMT, FV, fShow).
// Data: DY.L, DY.K, DY.E, ALW, G, PRI.
// ---------------- My league (Sleeper)
var ML={};
function slp(p){return fetch('https://api.sleeper.app/v1/'+p).then(function(r){if(!r.ok)throw new Error('Sleeper said '+r.status);return r.json()})}
function nth(n){return n+(['th','st','nd','rd'][(n%100-20)%10]||['th','st','nd','rd'][n%100]||'th')}
function sRender(){
  var L=D.DY.L,lg=ML.lg,rp=lg.roster_positions||[],cnt=function(p){return rp.filter(function(x){return x===p}).length};
  var sf=cnt('SUPER_FLEX')>0||cnt('QB')>1,vi=sf?5:4,rec=(lg.scoring_settings||{}).rec||0,idp=rp.some(function(x){return /IDP|^DL$|^LB$|^DB$/.test(x)});
  var pp=function(x){return x[6]==null?null:rec>=1?x[6]:rec<=0?x[7]:Math.round((x[6]+x[7])*5)/10};
  // league-wide position ranks by value and production among players with a value
  var VR={},PR={};['QB','RB','WR','TE'].forEach(function(p){var ks=Object.keys(L).filter(function(k){return L[k][1]===p&&L[k][vi]!=null});
    ks.slice().sort(function(a,b){return L[b][vi]-L[a][vi]}).forEach(function(k,i){VR[k]=i+1});
    ks.filter(function(k){return L[k][8]>=3&&L[k][6]!=null}).sort(function(a,b){return L[b][6]-L[a][6]}).forEach(function(k,i){PR[k]=i+1})});
  var nm={};ML.us.forEach(function(u){nm[u.user_id]=(u.metadata&&u.metadata.team_name)||u.display_name});
  var S=+lg.season,seasons=[S+1,S+2],rounds=Math.min((lg.settings&&lg.settings.draft_rounds)||4,4),own={};
  ML.ro.forEach(function(r){seasons.forEach(function(s){for(var d=1;d<=rounds;d++)own[s+'-'+d+'-'+r.roster_id]=r.roster_id})});
  ML.tp.forEach(function(t){var k=t.season+'-'+t.round+'-'+t.roster_id;if(k in own)own[k]=t.owner_id});
  var pv=function(s,d){var lab=s+' '+['','1st','2nd','3rd','4th'][d],k=D.DY.K.filter(function(x){return x[0]===lab})[0];return k?k[sf?2:1]:0};
  var me=null,teams=ML.ro.map(function(r){var ps=(r.players||[]).map(function(id){var x=L[id];return {id:id,x:x,v:x&&x[vi]!=null?x[vi]:0,taxi:(r.taxi||[]).indexOf(id)>-1,ir:(r.reserve||[]).indexOf(id)>-1}});
    var pk=[];Object.keys(own).forEach(function(k){if(own[k]===r.roster_id){var a=k.split('-');pk.push({s:+a[0],d:+a[1],from:+a[2],v:pv(+a[0],+a[1])})}});
    var T={r:r,name:nm[r.owner_id]||('Team '+r.roster_id),ps:ps,pk:pk,pv:ps.reduce(function(a,b){return a+b.v},0),kv:pk.reduce(function(a,b){return a+b.v},0),w:(r.settings||{}).wins||0,l:(r.settings||{}).losses||0};
    T.tv=T.pv+T.kv;var N={QB:cnt('QB')+(sf?1:0),RB:cnt('RB')+1,WR:cnt('WR')+1,TE:Math.max(cnt('TE'),1)};T.pos={};
    ['QB','RB','WR','TE'].forEach(function(p){T.pos[p]=ps.filter(function(o){return o.x&&o.x[1]===p}).map(function(o){return o.v}).sort(function(a,b){return b-a}).slice(0,N[p]).reduce(function(a,b){return a+b},0)});
    if(r.owner_id===ML.user.user_id||(r.co_owners||[]).indexOf(ML.user.user_id)>-1)me=T;return T});
  teams.sort(function(a,b){return b.tv-a.tv});teams.forEach(function(T,i){T.rk=i+1});
  ['QB','RB','WR','TE'].forEach(function(p){teams.slice().sort(function(a,b){return b.pos[p]-a.pos[p]}).forEach(function(T,i){T['r'+p]=i+1})});
  ML.teams=teams;ML.me=me;ML.vi=vi;ML.VR=VR;ML.PR=PR;ML.pp=pp;
  var n=teams.length,h=((lg.settings&&lg.settings.type!=null&&lg.settings.type!==2)?'<div class="card" style="margin-bottom:10px"><b>This is a '+({0:'redraft',1:'keeper'}[lg.settings.type]||'non-dynasty')+' league.</b> Long-term trade values matter less here. Switch to <b>Redraft</b> above for standings and waiver help.</div>':'')+'<h3>'+lg.name.replace(/</g,'&lt;')+'</h3><p class="sub">'+[(RL.M?RL.M.platform:''),n+' teams',({0:'Redraft',1:'Keeper',2:'Dynasty'}[lg.settings&&lg.settings.type]||''),(sf?'Superflex':'1QB'),(rec>=1?'PPR':rec<=0?'Standard':'Half PPR'),(idp?'IDP':'')].filter(Boolean).join(' · ')+'. Using '+(sf?'Superflex':'1QB')+' trade values.</p>';
  h+='<h3>Power rankings by roster value</h3><div class="wrap"><table><tr><th>#</th><th>Team</th><th>Record</th><th>Total value</th><th>Players</th><th>Picks</th><th>QB</th><th>RB</th><th>WR</th><th>TE</th></tr>'+teams.map(function(T){
    return '<tr'+(T===me?' class="me"':'')+'><td>'+T.rk+'</td><td class="nm">'+T.name.replace(/</g,'&lt;')+'</td><td>'+T.w+'-'+T.l+'</td><td><b>'+T.tv.toLocaleString()+'</b></td><td>'+T.pv.toLocaleString()+'</td><td>'+T.kv.toLocaleString()+'</td>'+['QB','RB','WR','TE'].map(function(p){var k=T['r'+p];return '<td><span class="'+(k<=3?'up':k>n-3?'dn':'')+'">'+nth(k)+'</span></td>'}).join('')+'</tr>'}).join('')+'</table></div>';
  if(!me){$('fmo').innerHTML=h+'<p class="sub">Couldn’t find your team in this league. For ESPN, add your team ID above.</p>';return}
  // advice
  var gap=function(o){return VR[o.id]&&PR[o.id]?VR[o.id]-PR[o.id]:null};
  var weak=['QB','RB','WR','TE'].filter(function(p){return me['r'+p]>n/2}).sort(function(a,b){return me['r'+b]-me['r'+a]}),strong=['QB','RB','WR','TE'].filter(function(p){return me['r'+p]<=3});
  var mine=me.ps.filter(function(o){return o.x&&o.v>0});
  var sell=mine.filter(function(o){var x=o.x,g=gap(o);return (x[1]==='RB'&&x[3]>=27&&o.v>=1000)||((x[1]==='WR'||x[1]==='TE')&&x[3]>=30&&o.v>=1000)||(g!=null&&g<=-15&&o.v>=1500)}).sort(function(a,b){return b.v-a.v}).slice(0,5);
  var others=[];teams.forEach(function(T){if(T!==me)T.ps.forEach(function(o){if(o.x&&o.v>0)others.push({o:o,T:T})})});
  var CUTS={QB:24,RB:36,WR:36,TE:18},buy=others.filter(function(e){var g=gap(e.o),pr=PR[e.o.id];return weak.indexOf(e.o.x[1])>-1&&g!=null&&g>=8&&pr&&pr<=CUTS[e.o.x[1]]&&e.o.x[3]!=null&&e.o.x[3]<=28}).sort(function(a,b){return gap(b.o)-gap(a.o)}).slice(0,8);
  var why2=function(o){var x=o.x,g=gap(o),w=[];if(x[1]==='RB'&&x[3]>=27)w.push('RB at '+x[3]+', value drops fast from here');if((x[1]==='WR'||x[1]==='TE')&&x[3]>=30)w.push('Age '+x[3]);if(g!=null&&g<=-15)w.push('Valued '+x[1]+VR[o.id]+', producing like '+x[1]+PR[o.id]);return w.join('; ')};
  h+='<h3>Your team: '+me.name.replace(/</g,'&lt;')+' ('+nth(me.rk)+' of '+n+' in value)</h3><ul class="adv">';
  ['QB','RB','WR','TE'].forEach(function(p){h+='<li><span class="tag '+p+'">'+p+'</span> room ranks <b>'+nth(me['r'+p])+'</b> of '+n+'</li>'});
  h+='</ul><h3>Advice</h3><ul class="adv">'+(weak.length?'<li>Biggest need: <b>'+weak.join(', ')+'</b>. Look at the buy targets below.</li>':'<li>No position ranks in the bottom half of the league. You’re balanced.</li>')+(strong.length?'<li>Strength to deal from: <b>'+strong.join(', ')+'</b>.</li>':'')+(sell.length?'<li>Sell-high candidates: '+sell.map(function(o){return '<b>'+o.x[0]+'</b> ('+why2(o)+')'}).join('; ')+'.</li>':'<li>No obvious sell-high players right now.</li>')+'</ul>';
  if(buy.length)h+='<h3>Buy targets at your weakest spots</h3><p class="sub">Players 28 or younger on other rosters who are producing like starters (top 36 RB or WR, top 24 QB, top 18 TE) and running ahead of their trade value.</p><div class="wrap"><table class="olt bt"><tr><th>Player</th><th>Pos</th><th>Age</th><th>Value</th><th>Valued</th><th>Producing like</th><th>Owner</th></tr>'+buy.map(function(e){var o=e.o,x=o.x;return '<tr><td class="nm">'+x[0]+'</td><td><span class="tag '+x[1]+'">'+x[1]+'</span></td><td>'+f(x[3],1)+'</td><td>'+o.v.toLocaleString()+'</td><td>'+x[1]+VR[o.id]+'</td><td>'+x[1]+PR[o.id]+'</td><td>'+e.T.name.replace(/</g,'&lt;')+'</td></tr>'}).join('')+'</table></div>';
  h+=RL.lineup||'';
  // roster
  var ros=me.ps.slice().sort(function(a,b){return b.v-a.v||((b.x&&b.x[10])||0)-((a.x&&a.x[10])||0)});
  h+='<h3>Your roster</h3><div class="wrap"><table><tr><th>Player</th><th>Pos</th><th>Team</th><th>Age</th><th>Value</th><th>Pos rank</th><th>Prod rank</th><th>'+(rec>=1?'PPR':rec<=0?'Std':'Half')+'/g</th><th>Last 3</th><th>IDP/g</th><th>Spot</th></tr>'+ros.map(function(o){var x=o.x;if(!x)return '<tr><td class="nm" colspan="11">Player '+o.id+' (not in our data)</td></tr>';var r={inj:x[11],dl:x[12]};
    return '<tr><td class="nm">'+x[0]+tags(r)+'</td><td><span class="tag '+x[1]+'">'+x[1]+'</span></td><td>'+x[2]+'</td><td>'+f(x[3],1)+'</td><td>'+(o.v?o.v.toLocaleString():'–')+'</td><td>'+(VR[o.id]?x[1]+VR[o.id]:'–')+'</td><td>'+(PR[o.id]?x[1]+PR[o.id]:'–')+'</td><td>'+f(pp(x),1)+'</td><td>'+f(x[9],1)+'</td><td>'+f(['QB','RB','WR','TE','K'].indexOf(x[1])<0?x[10]:null,1)+'</td><td>'+(o.ir?'IR':o.taxi?'Taxi':'')+'</td></tr>'}).join('')+'</table></div>';
  if(RL.M&&RL.M.platform==='Sleeper')h+='<h3>Your picks</h3><p class="sub">'+(me.pk.length?me.pk.sort(function(a,b){return a.s-b.s||a.d-b.d}).map(function(k){return k.s+' '+['','1st','2nd','3rd','4th'][k.d]+(k.from!==me.r.roster_id?' (from '+(teams.filter(function(T){return T.r.roster_id===k.from})[0]||{name:'?'}).name.replace(/</g,'&lt;')+')':'')}).join(', '):'None')+'</p>';
  // trade finder
  h+='<h3>Trade finder</h3><p class="sub">Pick one of your players to see players and picks on other teams worth about the same (within 15%).</p><div class="bar"><select id="tfp" aria-label="Your player">'+mine.sort(function(a,b){return b.v-a.v}).map(function(o){return '<option value="'+o.id+'">'+o.x[0]+' ('+o.x[1]+', '+o.v.toLocaleString()+')</option>'}).join('')+'</select><div class="seg" id="tfpos">'+['ALL','QB','RB','WR','TE','PICK'].map(function(p){return '<button data-p="'+p+'" aria-pressed="'+(p===(weak[0]||'ALL'))+'">'+(p==='ALL'?'All':p==='PICK'?'Picks':p)+'</button>'}).join('')+'</div></div><div id="tfo"></div>';
  h+='<div class="note">Roster values are DynastyProcess trade values (based on FantasyPros expert rankings), '+(sf?'Superflex':'1QB')+' version to match your league. Position room strength adds up the values of the players you would start there plus one depth player at RB and WR. Picks are valued as average picks for that round, since final draft order isn’t known yet. IDP players and kickers don’t have trade values, so they’re left out of the totals. League data comes straight from '+(RL.M?RL.M.platform:'Sleeper')+' each time you load it. The best lineup uses the same open formula as Start / sit.</div>';
  $('fmo').innerHTML=h;ML.tf=weak[0]||'ALL';$('tfp').onchange=tFind;
  $('tfpos').addEventListener('click',function(e){var p=e.target.dataset.p;if(!p)return;ML.tf=p;[].forEach.call($('tfpos').children,function(b){b.setAttribute('aria-pressed',b.dataset.p===p)});tFind()});tFind()}
function tFind(){var id=$('tfp').value,me=ML.me,o=me.ps.filter(function(x){return x.id===id})[0];if(!o){$('tfo').innerHTML='';return}var v=o.v,lo=v*.85,hi=v*1.15,out=[];
  ML.teams.forEach(function(T){if(T===me)return;T.ps.forEach(function(p){if(p.x&&p.v>=lo&&p.v<=hi&&(ML.tf==='ALL'||p.x[1]===ML.tf))out.push([p.x[0],p.x[1],p.x[3],p.v,T.name,p])});
    if(ML.tf==='ALL'||ML.tf==='PICK')T.pk.forEach(function(k){if(k.v>=lo&&k.v<=hi)out.push([k.s+' '+['','1st','2nd','3rd','4th'][k.d],'PICK',null,k.v,T.name,null])})});
  out.sort(function(a,b){return Math.abs(a[3]-v)-Math.abs(b[3]-v)});
  $('tfo').innerHTML=out.length?'<div class="wrap"><table class="olt"><tr><th>Player or pick</th><th>Pos</th><th>Age</th><th>Value</th><th>Vs yours</th><th>Producing like</th><th>Owner</th></tr>'+out.slice(0,25).map(function(r){var d=r[3]-v,p=r[5];return '<tr><td class="nm">'+r[0]+'</td><td>'+(r[1]==='PICK'?'Pick':'<span class="tag '+r[1]+'">'+r[1]+'</span>')+'</td><td>'+f(r[2],1)+'</td><td>'+r[3].toLocaleString()+'</td><td><span class="'+(d>0?'up':d<0?'dn':'')+'">'+(d>0?'+':'')+d.toLocaleString()+'</span></td><td>'+(p&&ML.PR[p.id]?p.x[1]+ML.PR[p.id]:'–')+'</td><td>'+r[4].replace(/</g,'&lt;')+'</td></tr>'}).join('')+'</table></div>':'<p class="sub">Nothing within 15% of that value at this position. Try All.</p>'}
// ---------------- Fantasy tab layout
var FMT=(function(){try{return localStorage.getItem('fmt')||'dyn'}catch(e){return 'dyn'}})(),FV='m';
function fShow(){if(FMT==='red'&&(FV==='r'||FV==='c'))FV='m';
  [].forEach.call($('fmt').children,function(b){b.setAttribute('aria-pressed',b.dataset.f===FMT)});
  [].forEach.call($('fv').children,function(b){b.hidden=FMT==='red'&&(b.dataset.x==='r'||b.dataset.x==='c');b.setAttribute('aria-pressed',b.dataset.x===FV)});
  $('fm').hidden=FV!=='m';$('fs').hidden=FV!=='s';$('sd').hidden=!(FV==='r'||FV==='c');$('dv').hidden=FV==='c';
  if(FV==='s')renderF();
  if(FV==='r'){if(['b','g','k'].indexOf(DS.v)<0){DS.v='b';[].forEach.call($('dv').children,function(b){b.setAttribute('aria-pressed',b.dataset.x==='b')})}renderD()}
  if(FV==='c'){DS.v='c';renderD()}}
// ---------------- My league (Sleeper + ESPN, dynasty or redraft)
var RL={};
function fMsg(x){$('fms').textContent=x}
var ESPOS={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'DEF'},ESLOT={0:'QB',2:'RB',4:'WR',6:'TE',23:'FLEX',7:'SF',16:'DEF',17:'K',20:'BN',21:'IR'};
var ELIG={QB:['QB'],RB:['RB'],WR:['WR'],TE:['TE'],FLEX:['RB','WR','TE'],SF:['QB','RB','WR','TE'],WRTE:['WR','TE'],WRRB:['RB','WR']};
function slotsFrom(list){var s={};list.forEach(function(x){var k={QB:'QB',RB:'RB',WR:'WR',TE:'TE',FLEX:'FLEX',SUPER_FLEX:'SF',REC_FLEX:'WRTE',WRRB_FLEX:'WRRB',SF:'SF'}[x];if(k)s[k]=(s[k]||0)+1});return s}
async function fSleeper(){var u=$('fsu').value.trim();if(!u){fMsg('Type your Sleeper username first.');return}try{localStorage.setItem('sleeper_user',u)}catch(e){}
  fMsg('Looking up '+u+'…');$('fmo').innerHTML='';
  try{var user=await slp('user/'+encodeURIComponent(u));if(!user||!user.user_id){fMsg('No Sleeper account found for “'+u+'”.');return}
    var stt=await slp('state/nfl'),S=+(stt.league_season||stt.season),lg=await slp('user/'+user.user_id+'/leagues/nfl/'+S);
    if(!lg.length){fMsg('No '+S+' NFL leagues found for '+u+'.');return}
    RL.user=user;var TY={0:'Redraft',1:'Keeper',2:'Dynasty'};
    $('fsls').innerHTML=lg.map(function(l){return '<option value="'+l.league_id+'">'+esc(l.name)+' · '+(TY[l.settings&&l.settings.type]||'League')+'</option>'}).join('');
    $('fsls').hidden=lg.length<2;$('fsls').onchange=function(){fSleeperLeague(this.value)};fSleeperLeague(lg[0].league_id)}
  catch(e){fMsg('Couldn’t reach Sleeper ('+e.message+'). Try again in a minute.')}}
async function fSleeperLeague(id){fMsg('Loading league…');
  try{var r=await Promise.all([slp('league/'+id),slp('league/'+id+'/rosters'),slp('league/'+id+'/users'),slp('league/'+id+'/traded_picks')]),lg=r[0],nm={};
    ML={lg:lg,ro:r[1],us:r[2],tp:r[3],user:RL.user};try{localStorage.setItem('last_league',JSON.stringify({p:'s',u:RL.user.username||$('fsu').value.trim(),id:id}))}catch(e){}
    r[2].forEach(function(u){nm[u.user_id]=(u.metadata&&u.metadata.team_name)||u.display_name});
    var M={platform:'Sleeper',ltype:lg.settings&&lg.settings.type,name:lg.name,rec:(lg.scoring_settings||{}).rec||0,type:({0:'Redraft',1:'Keeper',2:'Dynasty'})[lg.settings&&lg.settings.type]||'',slots:slotsFrom(lg.roster_positions||[]),
      teams:r[1].map(function(ro){var st=ro.starters||[],ir=ro.reserve||[],tx=ro.taxi||[];return {name:nm[ro.owner_id]||('Team '+ro.roster_id),me:ro.owner_id===RL.user.user_id||(ro.co_owners||[]).indexOf(RL.user.user_id)>-1,w:(ro.settings||{}).wins||0,l:(ro.settings||{}).losses||0,pf:((ro.settings||{}).fpts||0)+((ro.settings||{}).fpts_decimal||0)/100,
        ps:(ro.players||[]).map(function(k){return {k:k,st:ir.indexOf(k)>-1?'IR':tx.indexOf(k)>-1?'Taxi':st.indexOf(k)>-1?'S':'B'}})}})};
    fMsg('');RL.M=M;leagueRender()}catch(e){fMsg('Couldn’t load that league ('+e.message+').')}}
async function fEspn(){var id=$('fei').value.replace(/\D/g,''),tm=$('fet').value.replace(/\D/g,'');if(!id){fMsg('Type your ESPN league ID first. It’s the number after leagueId= in your league’s web address.');return}
  try{localStorage.setItem('espn_league',id);localStorage.setItem('espn_team',tm);localStorage.setItem('last_league',JSON.stringify({p:'e',id:id,t:tm}))}catch(e){}
  fMsg('Loading ESPN league…');$('fmo').innerHTML='';var S=(D.META&&D.META.season)||new Date().getFullYear();
  try{var res=await fetch('https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/'+S+'/segments/0/leagues/'+id+'?view=mTeam&view=mRoster&view=mSettings');
    if(res.status===401){fMsg('This ESPN league is private. The commissioner can turn on League Settings → Basic Settings → “Make league viewable to public”, then try again.');return}
    if(res.status===404){fMsg('No ESPN league found with ID '+id+' for '+S+'. Check the number in your league’s web address.');return}
    if(!res.ok)throw new Error('ESPN said '+res.status);var L=await res.json(),st=L.settings||{},rs=(st.rosterSettings||{}).lineupSlotCounts||{},sl={},rec=0;
    Object.keys(rs).forEach(function(k){var n=ESLOT[k];if(n&&ELIG[n])sl[n]=(sl[n]||0)+rs[k]});
    ((st.scoringSettings||{}).scoringItems||[]).forEach(function(s){if(s.statId===53)rec=s.points});
    var mem={};(L.members||[]).forEach(function(m){mem[m.id]=((m.firstName||'')+' '+(m.lastName||'')).trim()||m.displayName});
    var M={platform:'ESPN',name:st.name||('League '+id),rec:rec,type:'',slots:sl,teams:(L.teams||[]).map(function(T){var rcd=(T.record||{}).overall||{};
      return {name:T.name||((T.location||'')+' '+(T.nickname||'')).trim()||mem[(T.owners||[])[0]]||('Team '+T.id),me:tm?String(T.id)===tm:false,w:rcd.wins||0,l:rcd.losses||0,pf:rcd.pointsFor||0,
        ps:((T.roster||{}).entries||[]).map(function(en){var pl=(en.playerPoolEntry||{}).player||{},k=D.DY.E[String(en.playerId)];return {k:k||('espn:'+en.playerId),nm:pl.fullName,pos:ESPOS[pl.defaultPositionId],st:en.lineupSlotId===21?'IR':en.lineupSlotId===20?'B':'S'}})}})};
    var rp=[];Object.keys(sl).forEach(function(s){for(var i=0;i<sl[s];i++)rp.push({SF:'SUPER_FLEX',WRTE:'REC_FLEX',WRRB:'WRRB_FLEX'}[s]||s)});
    ML={lg:{name:M.name,season:S,roster_positions:rp,scoring_settings:{rec:rec},settings:{draft_rounds:4}},user:{user_id:'me'},tp:[],
      us:M.teams.map(function(T,i){return {user_id:T.me?'me':'t'+i,display_name:T.name,metadata:{team_name:T.name}}}),
      ro:M.teams.map(function(T,i){return {roster_id:i+1,owner_id:T.me?'me':'t'+i,players:T.ps.map(function(p){return p.k}),reserve:T.ps.filter(function(p){return p.st==='IR'}).map(function(p){return p.k}),taxi:[],settings:{wins:T.w,losses:T.l}}})};
    if(!M.teams.some(function(T){return T.me})){fMsg('Showing the whole league. Add your team ID (the number after teamId= in your team page’s web address) to get your lineup and waiver help.')}else fMsg('');
    RL.M=M;leagueRender()}catch(e){fMsg('Couldn’t load the ESPN league ('+e.message+').')}}
function lineupHTML(M){var rec=M.rec,me=M.teams.filter(function(T){return T.me})[0],n=M.teams.length;if(!me)return '';var B=me.best,cur=me.ps.filter(function(p){return p.st==='S'}).map(function(p){return p.k}),sugg=[];
    B.list.forEach(function(s){if(s.e&&cur.indexOf(s.e.p.k)<0)sugg.push(s.e)});
    var benchStarters=me.ps.filter(function(p){return p.st==='S'&&!B.used[p.k]&&wkPts(p.k,rec)&&wkPts(p.k,rec).pts!=null});
    var h='<h3>Your best lineup this week ('+f(B.total,1)+' adjusted points, '+nth(me.prk)+' of '+n+')</h3>';
    if(sugg.length)h+='<p class="sub"><b>Lineup changes to consider:</b> start '+sugg.map(function(e){return '<b>'+pName(e.p)+'</b>'}).join(', ')+(benchStarters.length?' over '+benchStarters.map(function(p){return '<b>'+pName(p)+'</b>'}).join(', '):'')+'.</p>';else h+='<p class="sub">Your current lineup already matches the best one.</p>';
    return h+'<div class="wrap"><table class="olt"><tr><th>Spot</th><th>Player</th><th>Opponent</th><th>Season</th><th>Last 3</th><th>Matchup</th><th>Grade</th><th>Adj. pts</th><th>Now</th></tr>'+B.list.map(function(s){if(!s.e)return '<tr><td>'+s.slot+'</td><td colspan="8" class="sub">Nobody eligible</td></tr>';var w=s.e.w,r={inj:w.inj,dl:w.dl};
      return '<tr><td>'+({SF:'SF',WRTE:'W/T',WRRB:'R/W'}[s.slot]||s.slot)+'</td><td class="nm">'+pName(s.e.p)+' <span class="tag '+w.pos+'">'+w.pos+'</span>'+tags(r)+'</td><td>'+w.opp+'</td><td>'+f(w.ppg,1)+'</td><td>'+f(w.l3,1)+'</td><td>'+w.m.toFixed(2)+'×</td><td><span class="gr g'+w.g+'">'+w.g+'</span></td><td><b>'+f(w.pts,1)+'</b></td><td>'+(cur.indexOf(s.e.p.k)>-1?'Starting':'<span class="up">Start</span>')+'</td></tr>'}).join('')+'</table></div>'}
function leagueRender(){var M=RL.M;if(!M)return;prepM(M);
  if(FMT==='dyn'){RL.lineup=lineupHTML(M);sRender()}else fRender(M);if(FV==='s'&&FSM==='me')renderMy()}
function fRender(M){var rec=M.rec,me=M.teams.filter(function(T){return T.me})[0],n=M.teams.length;
  var h='<h3>'+esc(M.name)+'</h3><p class="sub">'+M.platform+' · '+n+' teams'+(M.type?' · '+M.type:'')+' · '+(rec>=1?'PPR':rec<=0?'Standard':rec===.5?'Half PPR':rec+' per catch')+' · Starting spots: '+Object.keys(M.slots).map(function(s){return M.slots[s]+' '+({SF:'Superflex',WRTE:'WR/TE flex',WRRB:'RB/WR flex'}[s]||s)}).join(', ')+'. Kickers, defenses and IDP spots aren’t projected yet.</p>';
  h+='<h3>Standings and this week’s strength</h3><div class="wrap"><table><tr><th>Team</th><th>Record</th><th>Points for</th><th>Best lineup this week</th><th>Week rank</th></tr>'+M.teams.slice().sort(function(a,b){return b.w-a.w||b.pf-a.pf}).map(function(T){return '<tr'+(T.me?' class="me"':'')+'><td class="nm">'+esc(T.name)+'</td><td>'+T.w+'-'+T.l+'</td><td>'+f(+T.pf,1)+'</td><td>'+f(T.best.total,1)+'</td><td>'+nth(T.prk)+' of '+n+'</td></tr>'}).join('')+'</table></div>';
  if(M.ltype===2)h='<div class="card" style="margin-bottom:10px"><b>This is a dynasty league.</b> Switch to <b>Dynasty</b> above for trade values, buy and sell advice and the trade finder.</div>'+h;
  if(me){var B=me.best;h+=lineupHTML(M);
    var bench=me.ps.filter(function(p){return !B.used[p.k]});
    h+='<h3>Bench and the rest</h3><div class="wrap"><table class="olt bt"><tr><th>Player</th><th>Status</th><th>Opponent</th><th>Adj. pts</th></tr>'+bench.map(function(p){var w=wkPts(p.k,rec),x=D.DY.L[p.k];return '<tr><td class="nm">'+pName(p)+(x?' <span class="tag '+x[1]+'">'+x[1]+'</span>'+tags({inj:x[11],dl:x[12]}):(p.pos?' <span class="tag '+p.pos+'">'+p.pos+'</span>':''))+'</td><td>'+({S:'Starting',B:'Bench',IR:'IR',Taxi:'Taxi'}[p.st])+'</td><td>'+(w&&w.opp?w.opp:'–')+'</td><td>'+(w&&w.pts!=null?f(w.pts,1):'–')+'</td></tr>'}).join('')+'</table></div>';
    // waivers
    var own={};M.teams.forEach(function(T){T.ps.forEach(function(p){own[p.k]=1})});
    var weakest=Object.keys(M.slots).filter(function(s){return ['QB','RB','WR','TE'].indexOf(s)>-1}).map(function(s){var mine=B.list.filter(function(x){return x.slot===s&&x.e});return {s:s,v:mine.length?Math.min.apply(null,mine.map(function(x){return x.e.w.pts})):0}}).sort(function(a,b){return a.v-b.v})[0];
    var fa=Object.keys(D.DY.L).filter(function(k){var x=D.DY.L[k];return !own[k]&&['QB','RB','WR','TE'].indexOf(x[1])>-1&&x[8]>=1}).map(function(k){var w=wkPts(k,rec);return {k:k,w:w}}).filter(function(e){return e.w&&!e.w.out&&e.w.pts>0}).sort(function(a,b){return b.w.pts-a.w.pts});
    RL.fa=fa;RL.fap=weakest?weakest.s:'ALL';
    h+='<h3>Waiver wire</h3><p class="sub">Best players not on any roster in your league, by this week’s adjusted points'+(weakest?'. Your weakest starting spot this week is <b>'+weakest.s+'</b>':'')+'. Waiver claims and free agents can lag a little behind Sleeper and ESPN.</p><div class="bar"><div class="seg" id="fwp">'+['ALL','QB','RB','WR','TE'].map(function(p){return '<button data-p="'+p+'" aria-pressed="'+(p===RL.fap)+'">'+(p==='ALL'?'All':p)+'</button>'}).join('')+'</div></div><div id="fwo"></div>';
  }else h+='<p class="sub">Your team wasn’t found in this league, so lineup and waiver help are hidden.</p>';
  h+='<div class="note">Adjusted points use the same open formula as Start / sit: 85% season average plus 15% last 3, with about 4 games of last season mixed in early on games, times how soft this week’s opponent is at that position (adjusted for schedule). Players who are out, on IR or on bye count as 0. The best lineup fills each starting spot with your highest adjusted points, flex spots last. It’s a guide, not a projection model. League data loads straight from '+M.platform+' each time.</div>';
  $('fmo').innerHTML=h;if(me){$('fwp').addEventListener('click',function(e){var p=e.target.dataset.p;if(!p)return;RL.fap=p;[].forEach.call($('fwp').children,function(b){b.setAttribute('aria-pressed',b.dataset.p===p)});fWaiver()});fWaiver()}}
function fWaiver(){var rows=RL.fa.filter(function(e){return RL.fap==='ALL'||e.w.pos===RL.fap}).slice(0,20);
  $('fwo').innerHTML=rows.length?'<div class="wrap"><table class="olt bt"><tr><th>Player</th><th>Team</th><th>Opponent</th><th>Season</th><th>Last 3</th><th>Grade</th><th>Adj. pts</th></tr>'+rows.map(function(e){var w=e.w,x=w.x;return '<tr><td class="nm">'+x[0]+' <span class="tag '+w.pos+'">'+w.pos+'</span>'+tags({inj:w.inj,dl:w.dl})+'</td><td>'+x[2]+'</td><td>'+w.opp+'</td><td>'+f(w.ppg,1)+'</td><td>'+f(w.l3,1)+'</td><td><span class="gr g'+w.g+'">'+w.g+'</span></td><td><b>'+f(w.pts,1)+'</b></td></tr>'}).join('')+'</table></div>':'<p class="sub">No available players at that position with a game this week.</p>'}
function initFM(){$('fsm').addEventListener('click',function(e){var m=e.target.dataset.m;if(!m)return;FSM=m;[].forEach.call($('fsm').children,function(b){b.setAttribute('aria-pressed',b.dataset.m===m)});renderF()});
try{var su=localStorage.getItem('sleeper_user');if(su)$('fsu').value=su;var el=localStorage.getItem('espn_league');if(el)$('fei').value=el;var et=localStorage.getItem('espn_team');if(et)$('fet').value=et}catch(e){}
  $('fpl').addEventListener('click',function(e){var p=e.target.dataset.p;if(!p)return;[].forEach.call($('fpl').children,function(b){b.setAttribute('aria-pressed',b.dataset.p===p)});$('fsl').hidden=p!=='s';$('fel').hidden=p!=='e';fMsg('');$('fmo').innerHTML=''});
  $('fsgo').onclick=fSleeper;$('fsu').addEventListener('keydown',function(e){if(e.key==='Enter')fSleeper()});$('fego').onclick=fEspn;['fei','fet'].forEach(function(id){$(id).addEventListener('keydown',function(e){if(e.key==='Enter')fEspn()})})}
