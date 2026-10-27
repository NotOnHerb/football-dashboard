import pandas as pd, numpy as np, json, gzip, base64
import os, io, datetime, urllib.request
SEASON=2026
BASE='https://github.com/nflverse/nflverse-data/releases/download/'
def fetch(u): return io.BytesIO(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'football-dashboard'}),timeout=120).read())
ALIAS={'JAX':'JAC','JAC':'JAX','LA':'LAR','LAR':'LA','OAK':'LV'}
def games_from(s,teams):
    s=s[(s.season==SEASON)&(s.game_type=='REG')&s.away_score.isna()]
    if s.empty: return None
    s=s[s.week==s.week.min()].sort_values(['gameday','gametime']); out=[]
    for _,r in s.iterrows():
        fx=lambda t:t if t in teams else ALIAS.get(t,t)
        a,h=fx(r.away_team),fx(r.home_team)
        if a not in teams or h not in teams: return None
        dt=pd.to_datetime(str(r.gameday)+' '+str(r.gametime))
        out.append([a,h,'Wk %d, %s ET'%(r.week,dt.strftime('%a %b %d, %-I:%M %p'))])
    return out
def get_games(fb,teams):
    try:
        g=games_from(pd.read_csv(fetch(BASE+'schedules/games.csv')),teams)
        if g: print('schedule ok:',len(g),'games'); return g
    except Exception as e: print('schedule fetch failed, using saved list:',e)
    return fb
DATE=datetime.datetime.now(datetime.timezone.utc).strftime('%b %d, %Y at %H:%M UTC')
raw=pd.read_csv(os.environ['CSV_PATH'] if os.environ.get('CSV_PATH') else fetch(BASE+'stats_player/stats_player_regpost_%d.csv'%SEASON))
assert len(raw)>1000 and {'player_display_name','recent_team','fantasy_points_ppr','def_sacks','games'}<=set(raw.columns),'Downloaded file looks wrong, not updating the site'
print('rows downloaded:',len(raw))
df=raw[(raw.games<=20)&raw.position.notna()].copy()
N={'ARI':'Cardinals','ATL':'Falcons','BAL':'Ravens','BUF':'Bills','CAR':'Panthers','CHI':'Bears','CIN':'Bengals','CLE':'Browns','DAL':'Cowboys','DEN':'Broncos','DET':'Lions','GB':'Packers','HOU':'Texans','IND':'Colts','JAX':'Jaguars','JAC':'Jaguars','KC':'Chiefs','LA':'Rams','LAR':'Rams','LAC':'Chargers','LV':'Raiders','MIA':'Dolphins','MIN':'Vikings','NE':'Patriots','NO':'Saints','NYG':'Giants','NYJ':'Jets','PHI':'Eagles','PIT':'Steelers','SEA':'Seahawks','SF':'49ers','TB':'Buccaneers','TEN':'Titans','WAS':'Commanders'}
z=lambda s:s.replace(0,np.nan)
g=z(df.games); att=z(df.attempts); db=z(df.attempts+df.sacks_suffered); car=z(df.carries); tg=z(df.targets); rec=z(df.receptions)
c=pd.DataFrame(index=df.index)
c['fpg']=df.fantasy_points_ppr/g; c['ydsg']=(df.passing_yards+df.rushing_yards+df.receiving_yards)/g
c['td']=df.passing_tds+df.rushing_tds+df.receiving_tds
c['opp']=np.where(df.position=='QB',df.attempts+df.carries,df.carries+df.targets)/g
c['ts']=np.where(df.position=='QB',np.nan,df.target_share*100)
c['cmp']=df.completions/att*100; c['pyg']=df.passing_yards/g; c['ypa']=df.passing_yards/att; c['ptd']=df.passing_tds; c['int']=df.passing_interceptions
c['epadb']=df.passing_epa/db; c['pepa']=df.passing_epa; c['cpoe']=df.passing_cpoe; c['sackr']=df.sacks_suffered/db*100
c['adotq']=df.passing_air_yards/att; c['pacr']=df.pacr; c['fdq']=df.passing_first_downs/att*100; c['ryg']=df.rushing_yards/g
c['cg']=df.carries/g; c['ypc']=df.rushing_yards/car; c['rtd']=df.rushing_tds; c['repac']=df.rushing_epa/car; c['repa']=df.rushing_epa
c['rfd']=df.rushing_first_downs/car*100; c['tgg']=df.targets/g; c['recg']=df.receptions/g; c['recyg']=df.receiving_yards/g
c['cr']=df.receptions/tg*100; c['fuml']=df.fumbles_lost_total
c['ays']=df.air_yards_share*100; c['wopr']=df.wopr; c['racr']=df.racr; c['ypt']=df.receiving_yards/tg; c['epat']=df.receiving_epa/tg
c['reca']=df.receiving_epa; c['yacr']=df.receiving_yards_after_catch/rec; c['adot']=df.receiving_air_yards/tg; c['fdr']=df.receiving_first_downs/tg*100
com=[('PPR/g',1,'fpg'),('Yds/g',0,'ydsg'),('TD',0,'td'),('Opps/g',1,'opp'),('Tgt %',0,'ts')]
PC={'QB':com+[('Cmp %',1,'cmp'),('Pass yds/g',0,'pyg'),('Y/A',1,'ypa'),('Pass TD',0,'ptd'),('INT',0,'int'),('EPA/dropback',2,'epadb'),('Pass EPA',1,'pepa'),('CPOE',1,'cpoe'),('Sack %',1,'sackr'),('aDOT',1,'adotq'),('PACR',2,'pacr'),('1st down %',1,'fdq'),('Rush yds/g',0,'ryg')],
'RB':com+[('Carries/g',1,'cg'),('Rush yds/g',0,'ryg'),('Yds/carry',1,'ypc'),('Rush TD',0,'rtd'),('Rush EPA/att',2,'repac'),('Rush EPA',1,'repa'),('Rush 1st down %',1,'rfd'),('Targets/g',1,'tgg'),('Catches/g',1,'recg'),('Rec yds/g',0,'recyg'),('Catch %',0,'cr'),('Fum lost',0,'fuml')]}
wr=com+[('Targets/g',1,'tgg'),('Catches/g',1,'recg'),('Air yds share',0,'ays'),('WOPR',2,'wopr'),('RACR',2,'racr'),('Yds/target',1,'ypt'),('EPA/target',2,'epat'),('Rec EPA',1,'reca'),('YAC/catch',1,'yacr'),('Catch %',0,'cr'),('aDOT',1,'adot'),('1st down/tgt %',0,'fdr'),('Fum lost',0,'fuml')]
PC['WR']=wr; PC['TE']=wr
M={'QB':(df.attempts>=1,999),'RB':((df.carries+df.targets)>=5,999),'WR':(df.targets>=5,999),'TE':(df.targets>=3,999)}
df['fantasy_points']=df.fantasy_points.fillna(0)
P={};n=0
for pos,(m,k) in M.items():
    d=df[(df.position==pos)&m].sort_values('fantasy_points_ppr',ascending=False).head(k); P[pos]=[]
    for ix,r in d.iterrows():
        vals=[None if pd.isna(c.at[ix,e]) else round(float(c.at[ix,e]),dd) for _,dd,e in PC[pos]]
        vals=[int(v) if v is not None and dd==0 else v for v,(_,dd,_e) in zip(vals,PC[pos])]
        P[pos].append([r.player_display_name,r.recent_team,int(r.games),vals,round(float(r.fantasy_points/r.games),1)]); n+=1
PCout={p:[[l,d] for l,d,_ in v] for p,v in PC.items()}
# ---- teams
TC=[('GP',0,1,''),('Pass yds/g',0,1,'Offense'),('Rush yds/g',0,1,'Offense'),('Pass TD',0,1,'Offense'),('Rush TD',0,1,'Offense'),('Yds/attempt',1,1,'Offense'),('Yds/carry',1,1,'Offense'),('Pass EPA/dropback',2,1,'Offense'),('Rush EPA/carry',2,1,'Offense'),('Total pass EPA',0,1,'Offense'),('CPOE',1,1,'Offense'),('Sack % allowed',1,0,'Offense'),('Pass rate % (approx)',0,1,'Offense'),
('Sacks',0,1,'Defense'),('QB hits',0,1,'Defense'),('Tackles for loss',0,1,'Defense'),('Interceptions',0,1,'Defense'),('Passes defended',0,1,'Defense'),('Forced fumbles',0,1,'Defense'),('Defensive TDs',0,1,'Defense'),
('Giveaways',0,0,'Turnovers and discipline'),('Takeaways',0,1,'Turnovers and discipline'),('Turnover margin',0,1,'Turnovers and discipline'),('Penalties/g',1,0,'Turnovers and discipline'),('Penalty yds/g',0,0,'Turnovers and discipline'),('OL penalties',0,0,'Offensive line'),('OL penalty yds',0,0,'Offensive line'),('DL sacks',0,1,'Defensive line'),('DL QB hits',0,1,'Defensive line'),('DL tackles for loss',0,1,'Defensive line')]
T=[];LG=dict(give=0,take=0,sk=0,sks=0,py=0,ry=0)
for t,d in df.groupby('recent_team'):
    gp=int(d.games.max()); S=lambda col:float(d[col].sum()); dbs=S('attempts')+S('sacks_suffered'); cr=S('carries')
    cp=d.dropna(subset=['passing_cpoe']); cpoe=(cp.passing_cpoe*cp.attempts).sum()/cp.attempts.sum() if cp.attempts.sum()>0 else np.nan
    give=S('passing_interceptions')+S('fumbles_lost_total'); take=S('def_interceptions')+S('fumble_recovery_opp')
    v=[gp,S('passing_yards')/gp,S('rushing_yards')/gp,S('passing_tds'),S('rushing_tds'),S('passing_yards')/S('attempts'),S('rushing_yards')/cr,S('passing_epa')/dbs,S('rushing_epa')/cr,S('passing_epa'),cpoe,S('sacks_suffered')/dbs*100,dbs/(dbs+cr)*100,
       S('def_sacks'),S('def_qb_hits'),S('def_tackles_for_loss'),S('def_interceptions'),S('def_pass_defended'),S('def_fumbles_forced'),S('def_tds'),give,take,take-give,S('penalties')/gp,S('penalty_yards')/gp,d[d.position_group=='OL'].penalties.sum(),d[d.position_group=='OL'].penalty_yards.sum(),d[d.position_group=='DL'].def_sacks.sum(),d[d.position_group=='DL'].def_qb_hits.sum(),d[d.position_group=='DL'].def_tackles_for_loss.sum()]
    T.append([t]+[None if pd.isna(x) else (int(round(x)) if tc[1]==0 else round(float(x),tc[1])) for x,tc in zip(v,TC)])
    LG['give']+=give;LG['take']+=take;LG['sk']+=S('def_sacks');LG['sks']+=S('sacks_suffered');LG['py']+=S('passing_yards');LG['ry']+=S('receiving_yards')
print('CHECKS (should be close): giveaways',LG['give'],'vs takeaways',LG['take'],'| def sacks',LG['sk'],'vs sacks taken',LG['sks'],'| pass yds',LG['py'],'vs rec yds',LG['ry'])
dd=df[(df.position_group=='DL')|((df.position=='OLB')&(df.def_sacks>=2))].copy(); gg=z(dd.games)
dd['k']=dd.def_sacks+dd.def_qb_hits; dd=dd.sort_values('k',ascending=False)
DL=[[r.player_display_name,r.recent_team,r.position,int(r.games),round(float(r.def_sacks),1),round(float(r.def_sacks/r.games),2),int(r.def_qb_hits),round(float(r.def_qb_hits/r.games),2),int(r.def_tackles_for_loss),int(r.def_tackles_solo),int(r.def_tackles_solo+r.def_tackle_assists),int(r.def_pass_defended),int(r.def_fumbles_forced),round(float(r.k/r.games),2)] for _,r in dd.iterrows()]
oo=df[df.position_group=='OL'].sort_values('penalties',ascending=False)
OL=[[r.player_display_name,r.recent_team,r.position,int(r.penalties),int(r.penalty_yards),int(r.fumbles_lost_total)] for _,r in oo.iterrows()]
G_FALLBACK=[['NE','CHI','Thu Oct 22, 7:15 PM CT (live now)'],['PIT','NO','Sun Oct 25, 8:30 AM CT'],['IND','MIN','Sun Oct 25, 12:00 PM CT'],['MIA','NYJ','Sun Oct 25, 12:00 PM CT'],['CIN','BAL','Sun Oct 25, 12:00 PM CT'],['CLE','TEN','Sun Oct 25, 12:00 PM CT'],['TB','CAR','Sun Oct 25, 12:00 PM CT'],['SF','ATL','Sun Oct 25, 12:00 PM CT'],['NYG','HOU','Sun Oct 25, 12:00 PM CT'],['DEN','ARI','Sun Oct 25, 3:05 PM CT'],['LA','LV','Sun Oct 25, 3:25 PM CT'],['GB','DET','Sun Oct 25, 3:25 PM CT'],['KC','SEA','Sun Oct 25, 7:20 PM CT'],['DAL','PHI','Mon Oct 26, 7:15 PM CT']]
G=get_games(G_FALLBACK,{t[0] for t in T})
print('game teams missing from data:',sorted({x for g in G for x in g[:2]}-{t[0] for t in T}),'| DL',len(DL),'OL',len(OL))
dx=df[df.position_group.isin(['DL','LB','DB'])].copy()
for cc in ['def_sacks','def_qb_hits','def_interceptions','def_pass_defended','def_fumbles_forced','fumble_recovery_opp','def_tds','def_tackles_for_loss','def_tackles_solo','def_tackle_assists']: dx[cc]=dx[cc].fillna(0)
dx['tk']=dx.def_tackles_solo+dx.def_tackle_assists
dx=dx[(dx.tk>=1)|(dx.def_sacks>0)|(dx.def_interceptions>0)].sort_values('tk',ascending=False)
X=[[r.player_display_name,r.recent_team,r.position,int(r.games),int(r.tk),int(r.def_tackles_solo),round(float(r.tk/r.games),1),int(r.def_tackles_for_loss),round(float(r.def_sacks),1),int(r.def_qb_hits),int(r.def_interceptions),int(r.def_pass_defended),int(r.def_fumbles_forced),int(r.fumble_recovery_opp),int(r.def_tds)] for _,r in dx.iterrows()]
kx=df[df.position=='K'].copy()
for cc in [c for c in kx.columns if c.startswith(('fg_made_','fg_missed_'))]+['fg_made','fg_att','fg_missed','pat_made','pat_att']: kx[cc]=kx[cc].fillna(0)
a39=kx.fg_made_0_19+kx.fg_made_20_29+kx.fg_made_30_39; a50=kx.fg_made_50_59+kx.fg_made_60_; m40=kx.fg_missed_40_49+kx.fg_missed_50_59+kx.fg_missed_60_
kx['pts']=a39*3+kx.fg_made_40_49*4+a50*5+kx.pat_made-kx.fg_missed
print('kicker check: FG made by range matches total for',int(((a39+kx.fg_made_40_49+a50)==kx.fg_made).sum()),'of',len(kx))
kx=kx.assign(a39=a39,a50=a50,m40=m40).sort_values('pts',ascending=False)
K=[[r.player_display_name,r.recent_team,r.position,int(r.games),int(r.fg_made),int(r.fg_att),(round(float(r.fg_made/r.fg_att*100),1) if r.fg_att>0 else None),(int(r.fg_long) if pd.notna(r.fg_long) else None),int(r.a39),int(r.fg_made_40_49),int(r.a50),int(r.fg_missed),int(r.m40),int(r.pat_made),int(r.pat_att),int(r.pts),round(float(r.pts/r.games),1)] for _,r in kx.iterrows()]
print('defenders',len(X),'| kickers',len(K),'| top kicker',K[0][:2],K[0][-2:])
P['K']=[[r.player_display_name,r.recent_team,int(r.games),[round(float(r.pts/r.games),1),None,None,round(float(r.fg_att/r.games),1),None,int(r.fg_made),int(r.fg_att),(round(float(r.fg_made/r.fg_att*100),1) if r.fg_att>0 else None),(int(r.fg_long) if pd.notna(r.fg_long) else None),int(r.a39),int(r.fg_made_40_49),int(r.a50),int(r.fg_missed),int(r.m40),int(r.pat_made),int(r.pat_att),int(r.pts)],round(float(r.pts/r.games),1)] for _,r in kx.iterrows()]
PCout['K']=[['Pts/g',1],['Yds/g',0],['TD',0],['Opps/g',1],['Tgt %',0],['FG made',0],['FG att',0],['FG %',1],['Long',0],['0-39',0],['40-49',0],['50+',0],['Missed',0],['Missed 40+',0],['XP made',0],['XP att',0],['Fantasy pts',0]]
names={t:N[t] for t in set(df.recent_team)}
data=json.dumps({'P':P,'PC':PCout,'T':T,'TC':[list(x) for x in TC],'N':names,'X':X,'DL':DL,'OL':OL,'G':G},separators=(',',':'),ensure_ascii=False)
b64=base64.b64encode(gzip.compress(data.encode(),9)).decode()
html=open('template.html').read().replace('__B64__',b64).replace('__DATE__',DATE)
open('index.html','w').write(html)
print(n,'players | raw json',len(data),'| html bytes',len(html.encode()))
