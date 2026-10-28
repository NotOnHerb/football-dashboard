import pandas as pd, numpy as np, json, gzip, base64
import os, datetime
import sources
SEASON=sources.SEASON
META={'schema':2,'season':SEASON,'sources':{}}
def load(name):
    df,info=sources.load(name); META['sources'][name]=info; return df
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
        g=games_from(load('schedule'),teams)
        if g: print('schedule ok:',len(g),'games'); return g
    except Exception as e: print('schedule fetch failed, using saved list:',e)
    return fb
DATE=datetime.datetime.now(datetime.timezone.utc).strftime('%b %d, %Y at %H:%M UTC')
raw=load('season_stats')
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
        P[pos].append([r.player_display_name,r.recent_team,int(r.games),vals,round(float(r.fantasy_points/r.games),1),r.player_id]); n+=1
PCout={p:[[l,d] for l,d,_ in v] for p,v in PC.items()}
# ---- teams
# (label, decimals, higher is better, group, views: O=offense D=defense S=special teams; Whole team shows all)
TC=[('GP',0,1,'','ODS'),
('Total yds/g',0,1,'Offense','O'),('Pass yds/g',0,1,'Offense','O'),('Rush yds/g',0,1,'Offense','O'),('Pass TD',0,1,'Offense','O'),('Rush TD',0,1,'Offense','O'),('Yds/attempt',1,1,'Offense','O'),('Yds/carry',1,1,'Offense','O'),('Yds/play (approx)',1,1,'Offense','O'),('First downs/g',1,1,'Offense','O'),
('Pass att/g',1,1,'Play mix (run vs pass)','O'),('Rush att/g',1,1,'Play mix (run vs pass)','O'),('Dropbacks/g',1,1,'Play mix (run vs pass)','O'),('Pass rate % (approx)',0,1,'Play mix (run vs pass)','O'),('Run rate % (approx)',0,1,'Play mix (run vs pass)','O'),('Pass yds share %',0,1,'Play mix (run vs pass)','O'),('Pass TD share %',0,1,'Play mix (run vs pass)','O'),
('Pass EPA/dropback',2,1,'Efficiency','O'),('Rush EPA/carry',2,1,'Efficiency','O'),('Total pass EPA',0,1,'Efficiency','O'),('CPOE',1,1,'Efficiency','O'),('Sack % allowed',1,0,'Efficiency','O'),
('OL penalties',0,0,'Offensive line','O'),('OL penalty yds',0,0,'Offensive line','O'),
('Sacks',0,1,'Defense','D'),('Sacks/g',1,1,'Defense','D'),('QB hits',0,1,'Defense','D'),('Tackles for loss',0,1,'Defense','D'),('Interceptions',0,1,'Defense','D'),('Passes defended',0,1,'Defense','D'),('Forced fumbles',0,1,'Defense','D'),('Defensive TDs',0,1,'Defense','D'),
('DL sacks',0,1,'Defensive line','D'),('DL QB hits',0,1,'Defensive line','D'),('DL tackles for loss',0,1,'Defensive line','D'),
('Giveaways',0,0,'Turnovers and discipline','OD'),('Takeaways',0,1,'Turnovers and discipline','OD'),('Turnover margin',0,1,'Turnovers and discipline','OD'),('Penalties/g',1,0,'Turnovers and discipline','OD'),('Penalty yds/g',0,0,'Turnovers and discipline','OD'),
('FG made',0,1,'Kicking','S'),('FG att',0,1,'Kicking','S'),('FG %',1,1,'Kicking','S'),('Long FG',0,1,'Kicking','S'),('FG made 40+',0,1,'Kicking','S'),('FG missed',0,0,'Kicking','S'),('XP %',1,1,'Kicking','S'),
('Gross punt avg',1,1,'Punting','S'),('Net punt avg',1,1,'Punting','S'),('Punts inside 20',0,1,'Punting','S'),('Inside-20 %',0,1,'Punting','S'),('Punts blocked against',0,0,'Punting','S'),
('Punt return avg',1,1,'Returns','S'),('Kick return avg',1,1,'Returns','S'),('Return yds/g',1,1,'Returns','S'),('ST TDs',0,1,'Returns','S'),
('Kicks blocked (by D)',0,1,'Blocks','S'),('Kicks blocked against',0,0,'Blocks','S')]
T=[];TG={};LG=dict(give=0,take=0,sk=0,sks=0,py=0,ry=0,blk=0,blka=0)
dv=lambda a,b:(a/b if b else np.nan)
for t,d in df.groupby('recent_team'):
    gp=int(d.games.max()); TG[t]=gp; S=lambda col:float(d[col].fillna(0).sum())
    att=S('attempts'); dbs=att+S('sacks_suffered'); cr=S('carries'); pyd=S('passing_yards'); ryd=S('rushing_yards')
    cp=d.dropna(subset=['passing_cpoe']); cpoe=(cp.passing_cpoe*cp.attempts).sum()/cp.attempts.sum() if cp.attempts.sum()>0 else np.nan
    give=S('passing_interceptions')+S('fumbles_lost_total'); take=S('def_interceptions')+S('fumble_recovery_opp')
    ol=d[d.position_group=='OL']; dl=d[d.position_group=='DL']
    fg=S('fg_att'); pt=S('pt_att'); blk=S('def_punt_blocks')+S('def_fg_blocks')+S('def_pat_blocks'); blka=S('fg_blocked')+S('pat_blocked')+S('pt_blocked')
    V={'GP':gp,'Total yds/g':(pyd+ryd)/gp,'Pass yds/g':pyd/gp,'Rush yds/g':ryd/gp,'Pass TD':S('passing_tds'),'Rush TD':S('rushing_tds'),'Yds/attempt':dv(pyd,att),'Yds/carry':dv(ryd,cr),'Yds/play (approx)':dv(pyd+ryd,dbs+cr),'First downs/g':(S('passing_first_downs')+S('rushing_first_downs'))/gp,
     'Pass att/g':att/gp,'Rush att/g':cr/gp,'Dropbacks/g':dbs/gp,'Pass rate % (approx)':dv(dbs,dbs+cr)*100,'Run rate % (approx)':dv(cr,dbs+cr)*100,'Pass yds share %':dv(pyd,pyd+ryd)*100,'Pass TD share %':dv(S('passing_tds'),S('passing_tds')+S('rushing_tds'))*100,
     'Pass EPA/dropback':dv(S('passing_epa'),dbs),'Rush EPA/carry':dv(S('rushing_epa'),cr),'Total pass EPA':S('passing_epa'),'CPOE':cpoe,'Sack % allowed':dv(S('sacks_suffered'),dbs)*100,
     'OL penalties':ol.penalties.sum(),'OL penalty yds':ol.penalty_yards.sum(),
     'Sacks':S('def_sacks'),'Sacks/g':S('def_sacks')/gp,'QB hits':S('def_qb_hits'),'Tackles for loss':S('def_tackles_for_loss'),'Interceptions':S('def_interceptions'),'Passes defended':S('def_pass_defended'),'Forced fumbles':S('def_fumbles_forced'),'Defensive TDs':S('def_tds'),
     'DL sacks':dl.def_sacks.sum(),'DL QB hits':dl.def_qb_hits.sum(),'DL tackles for loss':dl.def_tackles_for_loss.sum(),
     'Giveaways':give,'Takeaways':take,'Turnover margin':take-give,'Penalties/g':S('penalties')/gp,'Penalty yds/g':S('penalty_yards')/gp,
     'FG made':S('fg_made'),'FG att':fg,'FG %':dv(S('fg_made'),fg)*100,'Long FG':d.fg_long.max(),'FG made 40+':S('fg_made_40_49')+S('fg_made_50_59')+S('fg_made_60_'),'FG missed':S('fg_missed'),'XP %':dv(S('pat_made'),S('pat_att'))*100,
     'Gross punt avg':dv(S('pt_yards'),pt),'Net punt avg':dv(S('pt_net_yards'),pt),'Punts inside 20':S('pt_inside_20'),'Inside-20 %':dv(S('pt_inside_20'),pt)*100,'Punts blocked against':S('pt_blocked'),
     'Punt return avg':dv(S('punt_return_yards'),S('punt_returns')),'Kick return avg':dv(S('kickoff_return_yards'),S('kickoff_returns')),'Return yds/g':(S('punt_return_yards')+S('kickoff_return_yards'))/gp,'ST TDs':S('special_teams_tds'),
     'Kicks blocked (by D)':blk,'Kicks blocked against':blka}
    T.append([t]+[None if pd.isna(V[tc[0]]) else (int(round(V[tc[0]])) if tc[1]==0 else round(float(V[tc[0]]),tc[1])) for tc in TC])
    LG['give']+=give;LG['take']+=take;LG['sk']+=S('def_sacks');LG['sks']+=S('sacks_suffered');LG['py']+=pyd;LG['ry']+=S('receiving_yards');LG['blk']+=blk;LG['blka']+=blka
print('CHECKS (should be close): giveaways',LG['give'],'vs takeaways',LG['take'],'| def sacks',LG['sk'],'vs sacks taken',LG['sks'],'| pass yds',LG['py'],'vs rec yds',LG['ry'],'| kicks blocked by D',LG['blk'],'vs against',LG['blka'])
dd=df[(df.position_group=='DL')|((df.position=='OLB')&(df.def_sacks>=2))].copy(); gg=z(dd.games)
dd['k']=dd.def_sacks+dd.def_qb_hits; dd=dd.sort_values('k',ascending=False)
DL=[[r.player_display_name,r.recent_team,r.position,int(r.games),round(float(r.def_sacks),1),round(float(r.def_sacks/r.games),2),int(r.def_qb_hits),round(float(r.def_qb_hits/r.games),2),int(r.def_tackles_for_loss),int(r.def_tackles_solo),int(r.def_tackles_solo+r.def_tackle_assists),int(r.def_pass_defended),int(r.def_fumbles_forced),round(float(r.k/r.games),2)] for _,r in dd.iterrows()]
oo=df[df.position_group=='OL'].sort_values('penalties',ascending=False)
OL=[[r.player_display_name,r.recent_team,r.position,int(r.penalties),int(r.penalty_yards),int(r.fumbles_lost_total)] for _,r in oo.iterrows()]
G_FALLBACK=[['NE','CHI','Thu Oct 22, 7:15 PM CT (live now)'],['PIT','NO','Sun Oct 25, 8:30 AM CT'],['IND','MIN','Sun Oct 25, 12:00 PM CT'],['MIA','NYJ','Sun Oct 25, 12:00 PM CT'],['CIN','BAL','Sun Oct 25, 12:00 PM CT'],['CLE','TEN','Sun Oct 25, 12:00 PM CT'],['TB','CAR','Sun Oct 25, 12:00 PM CT'],['SF','ATL','Sun Oct 25, 12:00 PM CT'],['NYG','HOU','Sun Oct 25, 12:00 PM CT'],['DEN','ARI','Sun Oct 25, 3:05 PM CT'],['LA','LV','Sun Oct 25, 3:25 PM CT'],['GB','DET','Sun Oct 25, 3:25 PM CT'],['KC','SEA','Sun Oct 25, 7:20 PM CT'],['DAL','PHI','Mon Oct 26, 7:15 PM CT']]
G=get_games(G_FALLBACK,{t[0] for t in T})
print('game teams missing from data:',sorted({x for g in G for x in g[:2]}-{t[0] for t in T}),'| DL',len(DL),'OL',len(OL))
dx=df[df.position_group.isin(['DL','LB','DB'])].copy()
for cc in ['def_sacks','def_qb_hits','def_interceptions','def_pass_defended','def_fumbles_forced','fumble_recovery_opp','def_tds','def_tackles_for_loss','def_tackles_solo','def_tackle_assists','def_safeties']: dx[cc]=dx[cc].fillna(0)
dx['idp']=dx.def_tackles_solo*1+dx.def_tackle_assists*.5+dx.def_tackles_for_loss*1+dx.def_sacks*3+dx.def_qb_hits*.5+dx.def_interceptions*3+dx.def_pass_defended*1+dx.def_fumbles_forced*3+dx.fumble_recovery_opp*2+dx.def_tds*6+dx.def_safeties*2
dx['tk']=dx.def_tackles_solo+dx.def_tackle_assists
dx=dx[(dx.tk>=1)|(dx.def_sacks>0)|(dx.def_interceptions>0)].sort_values('tk',ascending=False)
X=[[r.player_display_name,r.recent_team,r.position,int(r.games),int(r.tk),int(r.def_tackles_solo),round(float(r.tk/r.games),1),int(r.def_tackles_for_loss),round(float(r.def_sacks),1),int(r.def_qb_hits),int(r.def_interceptions),int(r.def_pass_defended),int(r.def_fumbles_forced),int(r.fumble_recovery_opp),int(r.def_tds),round(float(r.idp),1),round(float(r.idp/r.games),1),r.player_id] for _,r in dx.iterrows()]
kx=df[df.position=='K'].copy()
for cc in [c for c in kx.columns if c.startswith(('fg_made_','fg_missed_'))]+['fg_made','fg_att','fg_missed','pat_made','pat_att']: kx[cc]=kx[cc].fillna(0)
a39=kx.fg_made_0_19+kx.fg_made_20_29+kx.fg_made_30_39; a50=kx.fg_made_50_59+kx.fg_made_60_; m40=kx.fg_missed_40_49+kx.fg_missed_50_59+kx.fg_missed_60_
kx['pts']=a39*3+kx.fg_made_40_49*4+a50*5+kx.pat_made-kx.fg_missed
print('kicker check: FG made by range matches total for',int(((a39+kx.fg_made_40_49+a50)==kx.fg_made).sum()),'of',len(kx))
kx=kx.assign(a39=a39,a50=a50,m40=m40).sort_values('pts',ascending=False)
K=[[r.player_display_name,r.recent_team,r.position,int(r.games),int(r.fg_made),int(r.fg_att),(round(float(r.fg_made/r.fg_att*100),1) if r.fg_att>0 else None),(int(r.fg_long) if pd.notna(r.fg_long) else None),int(r.a39),int(r.fg_made_40_49),int(r.a50),int(r.fg_missed),int(r.m40),int(r.pat_made),int(r.pat_att),int(r.pts),round(float(r.pts/r.games),1)] for _,r in kx.iterrows()]
print('defenders',len(X),'| kickers',len(K),'| top kicker',K[0][:2],K[0][-2:])
P['K']=[[r.player_display_name,r.recent_team,int(r.games),[round(float(r.pts/r.games),1),None,None,round(float(r.fg_att/r.games),1),None,int(r.fg_made),int(r.fg_att),(round(float(r.fg_made/r.fg_att*100),1) if r.fg_att>0 else None),(int(r.fg_long) if pd.notna(r.fg_long) else None),int(r.a39),int(r.fg_made_40_49),int(r.a50),int(r.fg_missed),int(r.m40),int(r.pat_made),int(r.pat_att),int(r.pts)],round(float(r.pts/r.games),1),r.player_id] for _,r in kx.iterrows()]
PCout['K']=[['Pts/g',1],['Yds/g',0],['TD',0],['Opps/g',1],['Tgt %',0],['FG made',0],['FG att',0],['FG %',1],['Long',0],['0-39',0],['40-49',0],['50+',0],['Missed',0],['Missed 40+',0],['XP made',0],['XP att',0],['Fantasy pts',0]]
OLSTART={}
DLAB={}
def load_inj():
    try:
        i=load('injuries')
        i=i[(i.season==SEASON)&(i.week==i.week.max())&i.report_status.notna()]
        print('injury report ok: week',int(i.week.max()) if len(i) else '-','|',len(i),'players listed')
        out={r.gsis_id:[str(r.report_status),str(r.report_primary_injury) if pd.notna(r.report_primary_injury) else '',int(r.week)] for _,r in i.iterrows()}
        try:
            ro=load('rosters'); ro=ro[(ro.week==ro.week.max())&(ro.status=='RES')]
            for _,r in ro.iterrows():
                ir=str(r.status_description_abbr) in ('R01','R48')
                out[r.gsis_id]=['IR' if ir else 'Reserve','Injured reserve' if ir else 'Reserve list',int(r.week)]
            print('reserve list ok:',len(ro),'players')
        except Exception as ex: print('roster status fetch failed:',ex)
        return out
    except Exception as ex:
        print('injury fetch failed:',ex); return {}
INJ=load_inj()
def load_depth(teams):
    try:
        c=load('depth')
        dt=str(c.dt.max())[:10]; c=c[c.dt==c.dt.max()].dropna(subset=['player_name']).sort_values('pos_rank'); CALL=c.assign(team=c.team.map(lambda t:t if t in teams else ALIAS.get(t,t))); c=c.drop_duplicates(['team','pos_grp','pos_abb'])
        c=c.assign(team=c.team.map(lambda t:t if t in teams else ALIAS.get(t,t)))
        ST=df.drop_duplicates('player_id').set_index('player_id')
        base=c[c.pos_grp.str.startswith('Base',na=False)]
        raw_fr={};out={}
        for t in teams:
            ct=c[c.team==t]; bt=base[base.team==t]
            if bt.empty: continue
            sch='3-4' if bt.pos_grp.str.contains('3-4').any() else '4-3'
            slots=['LDE','NT','RDE','SLB','WLB'] if sch=='3-4' else ['LDE','LDT','RDT','RDE']
            ols=[]
            for sl in ['LT','LG','C','RG','RT']:
                r=ct[(ct.pos_abb==sl)&~ct.pos_grp.str.startswith('Base',na=False)&(ct.pos_grp!='Special Teams')]
                if r.empty: continue
                r=r.iloc[0]; s=ST.loc[r.gsis_id] if r.gsis_id in ST.index else None
                ols.append([sl,r.player_name,int(s.penalties) if s is not None and pd.notna(s.penalties) else 0,int(s.penalty_yards) if s is not None and pd.notna(s.penalty_yards) else 0])
            frs=[]
            for sl in slots:
                r=bt[bt.pos_abb==sl]
                if r.empty: continue
                r=r.iloc[0]; s=ST.loc[r.gsis_id] if r.gsis_id in ST.index else None
                g=lambda col:float(s[col]) if s is not None and pd.notna(s[col]) else 0.0
                dpg=(g('def_sacks')+g('def_qb_hits')+g('def_tackles_for_loss'))/max(TG.get(t,1),1)
                frs.append([sl,r.player_name,round(g('def_sacks'),1),int(g('def_qb_hits')),int(g('def_tackles_for_loss')),0,round(dpg,2)])
            dbs=[]
            used=set(); ball=CALL[(CALL.team==t)&CALL.pos_grp.str.startswith('Base',na=False)]
            for sl in ['LCB','RCB','NB','SS','FS']:
                r=ball[(ball.pos_abb==sl)&~ball.gsis_id.isin(used)]
                if r.empty: continue
                r=r.iloc[0]; used.add(r.gsis_id); s=ST.loc[r.gsis_id] if r.gsis_id in ST.index else None
                g=lambda col:float(s[col]) if s is not None and pd.notna(s[col]) else 0.0
                dbs.append([sl,r.player_name,int(g('def_interceptions')),int(g('def_pass_defended')),int(g('def_tackles_solo')+g('def_tackle_assists'))])
            for sl in ['LT','LG','C','RG','RT']:
                r=ct[(ct.pos_abb==sl)&~ct.pos_grp.str.startswith('Base',na=False)&(ct.pos_grp!='Special Teams')]
                if not r.empty: OLSTART[r.iloc[0].gsis_id]=(t,sl,r.iloc[0].player_name); DLAB[r.iloc[0].gsis_id]=[sl,True]
            sk={}
            for _,r in ball.drop_duplicates('gsis_id').iterrows():
                DLAB.setdefault(r.gsis_id,[r.pos_abb+('' if r.pos_rank==1 else str(int(r.pos_rank))),bool(r.pos_rank==1)])
            for p,n in [('QB',1),('RB',2),('WR',3),('TE',1)]:
                rall=CALL[(CALL.team==t)&(CALL.pos_abb==p)&~CALL.pos_grp.str.startswith('Base',na=False)&(CALL.pos_grp!='Special Teams')].drop_duplicates('gsis_id')
                for k,(_,r) in enumerate(rall.iterrows()): DLAB.setdefault(r.gsis_id,[p+str(k+1),k<n])
                rr=rall.head(n+4)
                lst=[]
                for _,r in rr.iterrows():
                    s=ST.loc[r.gsis_id] if r.gsis_id in ST.index else None
                    gm=float(s.games) if s is not None and pd.notna(s.games) and s.games>0 else 0
                    pp=round(float(s.fantasy_points_ppr)/gm,1) if gm else None; sd=round(float(s.fantasy_points)/gm,1) if gm else None
                    lst.append([r.player_name,pp,sd,INJ.get(r.gsis_id)])
                sk[p]=lst
            out[t]={'s':sch,'ol':ols,'fr':frs,'db':dbs,'sk':sk,'n':{'QB':1,'RB':2,'WR':3,'TE':1}}
        allv=np.array([x[6] for v in out.values() for x in v['fr']])
        p90,p75,p50=np.percentile(allv,[90,75,50])
        for v in out.values():
            for x in v['fr']: x[5]=4 if x[6]>=p90 else 3 if x[6]>=p75 else 2 if x[6]>=p50 else 1
        print('depth charts ok:',len(out),'teams | as of',dt,'| 3-4 teams',sum(1 for v in out.values() if v['s']=='3-4'),'| thresholds',round(p90,2),round(p75,2),round(p50,2))
        return {'dt':dt,'T':out}
    except Exception as ex:
        print('depth chart fetch failed, matchups will use stats only:',ex); return None
DEP=load_depth({t[0] for t in T})
OLP={}
for _,r in df[df.position_group=='OL'].iterrows():
    OLP[r.player_id]=[r.player_display_name,r.recent_team,r.position,int(r.games),'–',int(r.penalties or 0),int(r.penalty_yards or 0),INJ.get(r.player_id)]
for gid,(t,sl,nm) in OLSTART.items():
    if gid in OLP: OLP[gid][4]=sl; OLP[gid][1]=t
    else: OLP[gid]=[nm,t,sl,None,sl,0,0,INJ.get(gid)]
OLP=sorted(OLP.values(),key=lambda x:(x[4]=='–',x[1],['LT','LG','C','RG','RT','–'].index(x[4]) if x[4] in ['LT','LG','C','RG','RT','–'] else 9))
print('OL players',len(OLP),'| starters',sum(1 for x in OLP if x[4]!='–'))
WK=None
def load_allowed():
    global WK
    try:
        w=load('weekly_stats')
        w=w[(w.season==SEASON)&(w.season_type=='REG')&w.position.isin(['QB','RB','WR','TE'])].copy()
        for c in ['fantasy_points','fantasy_points_ppr','passing_yards','rushing_yards','receiving_yards','passing_tds','rushing_tds','receiving_tds','receptions']: w[c]=w[c].fillna(0)
        fx=lambda t:t if t in N else ALIAS.get(t,t)
        w['team']=w.team.map(fx); w['opponent_team']=w.opponent_team.map(fx)
        w['yds']=np.where(w.position=='QB',w.passing_yards+w.rushing_yards,np.where(w.position=='RB',w.rushing_yards+w.receiving_yards,w.receiving_yards))
        w['td']=w.passing_tds+w.rushing_tds+w.receiving_tds
        out={}
        for side,key in [('a','opponent_team'),('s','team')]:
            gp=w.groupby(key).game_id.nunique()
            agg=w.groupby([key,'position'])[['fantasy_points_ppr','fantasy_points','yds','td','receptions']].sum()
            for (t,p),v in agg.iterrows():
                o=out.setdefault(t,{'g':int(gp[t]),'a':{},'s':{}})
                o[side][p]=[round(float(x)/gp[t],2) for x in v.values]
        WK=w.copy()
        # strength of schedule: each game's points allowed minus what that offense normally scores at the position
        gt=w[['game_id','team','opponent_team']].drop_duplicates()
        gt=gt.assign(k=1).merge(pd.DataFrame({'position':['QB','RB','WR','TE'],'k':1}),on='k').drop(columns='k')
        gs=w.groupby(['game_id','team','opponent_team','position'])[['fantasy_points_ppr','fantasy_points']].sum().reset_index()
        gs=gt.merge(gs,on=['game_id','team','opponent_team','position'],how='left').fillna({'fantasy_points_ppr':0,'fantasy_points':0})
        oavg=gs.groupby(['team','position'])[['fantasy_points_ppr','fantasy_points']].transform('mean')
        gs['dpp']=gs.fantasy_points_ppr-oavg.fantasy_points_ppr; gs['dsd']=gs.fantasy_points-oavg.fantasy_points
        lg=gs.groupby('position')[['fantasy_points_ppr','fantasy_points']].mean()
        adj=gs.groupby(['opponent_team','position'])[['dpp','dsd']].mean()
        for (t,p),v in adj.iterrows():
            if t in out: out[t].setdefault('aa',{})[p]=[round(float(lg.loc[p,'fantasy_points_ppr']+v.dpp),2),round(float(lg.loc[p,'fantasy_points']+v.dsd),2)]
        LGAVG={p:[round(float(lg.loc[p,'fantasy_points_ppr']),2),round(float(lg.loc[p,'fantasy_points']),2)] for p in lg.index}
        print('SOS check (league avg of adjusted should equal plain avg): RB',round(float(np.mean([v['aa']['RB'][0] for v in out.values()])),2),'vs',LGAVG['RB'][0])
        tot_a=sum(v['a'][p][0]*v['g'] for v in out.values() for p in v['a']); tot_s=sum(v['s'][p][0]*v['g'] for v in out.values() for p in v['s'])
        print('allowed ok: weeks',int(w.week.min()),'-',int(w.week.max()),'| teams',len(out),'| PPR allowed',round(tot_a),'vs scored',round(tot_s))
        return {'wk':int(w.week.max()),'T':out,'lg':LGAVG}
    except Exception as ex:
        print('weekly stats fetch failed, skill matchups hidden:',ex); return None
ALW=load_allowed()
# ---- recent form (last 3 games played) and snap share
FORM={}
if WK is not None:
    for pid,g in WK.sort_values('week').groupby('player_id'):
        l3=g.tail(3); FORM[pid]=[round(float(l3.fantasy_points_ppr.mean()),1),round(float(l3.fantasy_points.mean()),1),None,None]
SNAP={}
try:
    sn=load('snaps'); pl=load('players')
    sn=sn.merge(pl[['pfr_id','gsis_id']].dropna().drop_duplicates('pfr_id'),left_on='pfr_player_id',right_on='pfr_id',how='inner')
    sn['pct']=np.where(sn.offense_pct.fillna(0)>=sn.defense_pct.fillna(0),sn.offense_pct.fillna(0),sn.defense_pct.fillna(0))*100
    for gid,g in sn.sort_values('week').groupby('gsis_id'): SNAP[gid]=[round(float(g.pct.mean())),round(float(g.tail(3).pct.mean()))]
    print('snap shares ok:',len(SNAP),'players')
except Exception as ex:
    pl=None; print('snap counts failed:',ex)
# ---- dynasty board
DY=None
try:
    dv=load('dynasty_values')
    pk=dv[dv.pos=='PICK'].copy(); pk['yr']=pk.player.str.extract(r'^(\d{4})')[0].astype(float)
    pk=pk[pk.yr>SEASON]
    picks=[[r.player,int(r.value_1qb),int(r.value_2qb)] for _,r in pk.sort_values('value_1qb',ascending=False).iterrows()]
    pv=dv[dv.pos.isin(['QB','RB','WR','TE'])].copy()
    bio=pl.drop_duplicates('gsis_id').set_index('gsis_id') if pl is not None else None
    sst=df.drop_duplicates('player_id').set_index('player_id')
    rows=[]
    for _,r in pv.iterrows():
        g=r.gsis_id if pd.notna(r.gsis_id) else None
        b_=bio.loc[g] if (bio is not None and g in bio.index) else None
        s_=sst.loc[g] if g in sst.index else None
        gm=float(s_.games) if s_ is not None and s_.games>0 else 0
        fp=round(float(s_.fantasy_points_ppr)/gm,1) if gm else None
        rows.append([r.player,r.pos,r.team if pd.notna(r.team) else 'FA',round(float(r.age),1) if pd.notna(r.age) else None,
            int(b_.draft_year) if b_ is not None and pd.notna(b_.draft_year) else (int(r.draft_year) if pd.notna(r.draft_year) else None),
            int(b_.draft_round) if b_ is not None and pd.notna(b_.draft_round) else None,
            str(b_.college_name) if b_ is not None and pd.notna(b_.college_name) else '',
            int(r.value_1qb),int(r.value_2qb),int(gm) if gm else 0,fp,
            (FORM.get(g) or [None])[0],(SNAP.get(g) or [None,None])[0],(SNAP.get(g) or [None,None])[1],INJ.get(g),DLAB.get(g),g])
    DY={'P':rows,'K':picks}
    # ---- Sleeper lookup: sleeper_id -> [name,pos,team,age,v1qb,v2qb,ppr/g,std/g,gp,last3 ppr,idp/g,inj,depth]
    ids=load('player_ids').dropna(subset=['sleeper_id','gsis_id']).drop_duplicates('sleeper_id')
    VAL={r.gsis_id:(int(r.value_1qb),int(r.value_2qb),r.age) for _,r in pv.dropna(subset=['gsis_id']).iterrows()}
    IDPG={}
    for _,r in dx.iterrows(): IDPG[r.player_id]=round(float(r.idp/r.games),1) if r.games else None
    KPG={r.player_id:round(float(r.pts/r.games),1) for _,r in kx.iterrows() if r.games}
    LK={};EM={}
    for _,r in ids.iterrows():
        g=r.gsis_id; s_=sst.loc[g] if g in sst.index else None
        if s_ is None and g not in VAL: continue
        gm=int(s_.games) if s_ is not None and s_.games>0 else 0
        v=VAL.get(g,(None,None,None)); age=v[2] if v[2]==v[2] and v[2] is not None else (r.age if pd.notna(r.age) else None)
        pos=str(s_.position) if s_ is not None and pd.notna(s_.position) else str(r.position)
        LK[str(int(float(r.sleeper_id))) if str(r.sleeper_id).replace('.','',1).isdigit() else str(r.sleeper_id)]=[
            (s_.player_display_name if s_ is not None else r['name']),pos,(s_.recent_team if s_ is not None else (r.team if pd.notna(r.team) else 'FA')),
            round(float(age),1) if age is not None else None,v[0],v[1],
            round(float(s_.fantasy_points_ppr)/gm,1) if gm else None,round(float(s_.fantasy_points)/gm,1) if gm else None,gm,
            (FORM.get(g) or [None])[0],IDPG.get(g) if g in IDPG else KPG.get(g),INJ.get(g),DLAB.get(g),(FORM.get(g) or [None,None])[1]]
        if pd.notna(r.espn_id): EM[str(int(float(r.espn_id)))]=list(LK)[-1]
    DY['L']=LK;DY['E']=EM
    print('sleeper lookup ok:',len(LK),'players | with value',sum(1 for x in LK.values() if x[4] is not None),'| espn ids',len(EM))
    print('dynasty ok:',len(rows),'players |',len(picks),'future picks | matched to stats',sum(1 for x in rows if x[9] is not None))
except Exception as ex:
    print('dynasty values failed:',ex)
# ---- college prospects (CollegeFootballData.com)
CF=None
try:
    cd=load('college')
    st=cd['stats'].copy(); st['stat']=pd.to_numeric(st.stat,errors='coerce'); st['playerId']=st.playerId.astype(str)
    st=st[st.position.isin(['QB','RB','WR','TE'])]
    wide=st.pivot_table(index='playerId',columns=['category','statType'],values='stat',aggfunc='first')
    wide.columns=[a[:4]+'_'+b_ for a,b_ in wide.columns]
    info=st.drop_duplicates('playerId').set_index('playerId')[['player','position','team','conference']]
    W_=info.join(wide)
    for c_ in ['rece_YDS','rush_YDS']:
        if c_ not in W_: W_[c_]=np.nan
    tr=W_.groupby('team').rece_YDS.sum(); tu=W_.groupby('team').rush_YDS.sum()
    W_['rec_share']=W_.rece_YDS/W_.team.map(tr).replace(0,np.nan)*100; W_['rush_share']=W_.rush_YDS/W_.team.map(tu).replace(0,np.nan)*100
    us=cd['usage']; us['id']=us['id'].astype(str); us=us.drop_duplicates('id').set_index('id')
    pp=cd['ppa']; pp['id']=pp['id'].astype(str); pp=pp.drop_duplicates('id').set_index('id')
    ro=cd['roster']; ro['id']=ro['id'].astype(str); ro=ro.drop_duplicates('id').set_index('id')
    rc=cd['recruits']; rc=rc.dropna(subset=['stars'])
    by_ath={str(int(a)):r for a,r in rc.dropna(subset=['athleteId']).set_index('athleteId').iterrows()} if 'athleteId' in rc else {}
    by_id={str(i):r for i,r in rc.set_index('id').iterrows()}
    g_=lambda s_,k:(float(s_[k]) if k in s_ and pd.notna(s_[k]) else None)
    rows=[]
    for pid,r in W_.iterrows():
        att,car,rec=g_(r,'pass_ATT') or 0,g_(r,'rush_CAR') or 0,g_(r,'rece_REC') or 0
        p=r.position
        if not ((p=='QB' and att>=60) or (p=='RB' and (car>=40 or rec>=15)) or (p in('WR','TE') and rec>=12)): continue
        R=ro.loc[pid] if pid in ro.index else None
        cls=int(R['year']) if R is not None and pd.notna(R['year']) and 1<=int(R['year'])<=5 else None
        rr=by_ath.get(pid)
        if rr is None and R is not None and isinstance(R.get('recruitIds'),list):
            for x in R['recruitIds']:
                if str(x) in by_id: rr=by_id[str(x)]; break
        hs=int(rr['year']) if rr is not None and pd.notna(rr['year']) else None
        if hs is not None and 1<=SEASON-hs+1<=5: cls=SEASON-hs+1
        elif cls==1: cls=None
        elig=(hs<=SEASON-2) if hs is not None else ((cls>=3) if cls is not None else None)
        U=us.loc[pid] if pid in us.index else None; PA=pp.loc[pid] if pid in pp.index else None
        rd=lambda v,k=1:None if v is None or v!=v else round(float(v),k)
        rows.append([r.player,p,r.team,r.conference,cls,int(rr['stars']) if rr is not None else None,int(rr['ranking']) if rr is not None and pd.notna(rr['ranking']) else None,hs,
            rd(U['usage.overall']*100 if U is not None and 'usage.overall' in U and pd.notna(U['usage.overall']) else None,0),
            rd(PA['averagePPA.all'] if PA is not None and 'averagePPA.all' in PA else None,2),rd(PA['totalPPA.all'] if PA is not None and 'totalPPA.all' in PA else None,1),elig,
            rd(g_(r,'pass_ATT'),0),rd(g_(r,'pass_PCT')*100 if g_(r,'pass_PCT') is not None and g_(r,'pass_PCT')<=1 else g_(r,'pass_PCT'),1),rd(g_(r,'pass_YDS'),0),rd(g_(r,'pass_TD'),0),rd(g_(r,'pass_INT'),0),rd(g_(r,'pass_YPA'),1),
            rd(g_(r,'rush_CAR'),0),rd(g_(r,'rush_YDS'),0),rd(g_(r,'rush_TD'),0),rd(g_(r,'rush_YPC'),1),
            rd(g_(r,'rece_REC'),0),rd(g_(r,'rece_YDS'),0),rd(g_(r,'rece_TD'),0),rd(g_(r,'rece_YPR'),1),
            rd(r.rec_share,0),rd(r.rush_share,0),
            int(R['height']) if R is not None and pd.notna(R.get('height')) else None,int(R['weight']) if R is not None and pd.notna(R.get('weight')) else None])
    # ---- team games played (for per-game college fantasy points)
    TGP={}
    gm_=cd.get('games')
    if gm_ is not None and len(gm_):
        hc=next((c for c in ['homeTeam','home_team'] if c in gm_),None); ac=next((c for c in ['awayTeam','away_team'] if c in gm_),None); cc=next((c for c in ['completed'] if c in gm_),None)
        if hc and ac:
            g2=gm_[gm_[cc]==True] if cc else gm_
            for t_ in list(g2[hc])+list(g2[ac]): TGP[t_]=TGP.get(t_,0)+1
    print('college team games:',len(TGP),'teams' if TGP else '(unavailable, per-game hidden)')
    # ---- college fantasy points and dynasty score
    P4C={'SEC','Big Ten','Big 12','ACC','FBS Independents'}; G5C={'American Athletic','Mountain West','Sun Belt','Mid-American','Conference USA','Pac-12'}
    z0=lambda v:v or 0
    for r in rows:
        ppr=z0(r[14])*.04+z0(r[15])*4-z0(r[16])*2+z0(r[19])*.1+z0(r[20])*6+z0(r[23])*.1+z0(r[24])*6
        r+= [None,None,round(ppr+z0(r[22]),1),round(ppr,1),TGP.get(r[2])]
    YOUTH={1:1.0,2:.85,3:.6,4:.35,5:.2}; PED={5:1.0,4:.75,3:.45,2:.2}
    W={'WR':[(26,.35),(10,.25),(9,.10),(23,.10)],'TE':[(26,.35),(10,.25),(9,.10),(23,.10)],'RB':[(27,.25),(10,.25),(9,.10),(23,.10)],'QB':[(9,.30),(10,.30),(13,.10),(19,.10)]}
    for pos,ws in W.items():
        grp=[r for r in rows if r[1]==pos]
        pct={}
        for idx,_ in ws:
            vals=sorted(r[idx] for r in grp if r[idx] is not None)
            pct[idx]=lambda v,vals=vals:(sum(1 for x in vals if x<=v)/len(vals)) if (v is not None and vals) else .3
        wp,wy=(.15,.15) if pos=='RB' else (.10,.10)
        for r in grp:
            sc=sum(w*pct[i](r[i]) for i,w in ws)+wp*PED.get(r[5],.3)+wy*YOUTH.get(r[4],.4)
            cf=1.0 if r[3] in P4C else .88 if r[3] in G5C else .75
            r[30]=round(sc*cf*100,1)
        ss=sorted(r[30] for r in grp)
        for r in grp:
            q=sum(1 for x in ss if x<=r[30])/len(ss)
            r[31]='A+' if q>=.98 else 'A' if q>=.95 else 'A-' if q>=.90 else 'B+' if q>=.82 else 'B' if q>=.70 else 'B-' if q>=.55 else 'C+' if q>=.40 else 'C' if q>=.25 else 'D'
    # ---- consensus big board (boards/boards_YYYY.csv, saved from published boards)
    import re as _re, os as _os
    def _nm(s):
        s=str(s).lower().replace('’',"'"); s=_re.sub(r"[.,']",'',s); s=_re.sub(r'\b(jr|sr|ii|iii|iv|v)\b','',s); return _re.sub(r'\s+',' ',s).strip()
    ALIAS_N={'ryan williams':'ryan colemanwilliams','ryan coleman-williams':'ryan colemanwilliams','kelly jones':'kelley jones','william echoles':'will echoles','gregory johnson':'greg johnson','matayo uigalelei':'matayo uiagalelei','tae johnson':'brauntae johnson'}
    def key(n):
        k=_nm(n); k=ALIAS_N.get(k,k); return k.replace('-','')
    CB=None; bf='boards/boards_%d.csv'%(SEASON+1)
    if _os.path.exists(bf):
        bd=pd.read_csv(bf); bd['k']=bd.name.map(key)
        srcs=bd.groupby('source').agg(url=('url','first'),updated=('updated','first'),blen=('rank','max')).reset_index()
        allk=bd.drop_duplicates('k').set_index('k')
        cons=[]
        for k_,g in bd.groupby('k'):
            rk={r.source:int(r['rank']) for _,r in g.iterrows()}
            if len(rk)<2: continue
            avg=sum(rk.get(s.source,int(s.blen)+1) for _,s in srcs.iterrows())/len(srcs)
            pm=g.pos.replace({'DE':'EDGE','OLB':'EDGE','DL':'DT','G':'IOL','C':'IOL'}).mode().iloc[0]
            cons.append([g.name.mode().iloc[0],pm,g.school.mode().iloc[0],round(avg,1),len(rk),min(rk.values()),max(rk.values()),k_]+[rk.get(s.source) for _,s in srcs.iterrows()])
        cons.sort(key=lambda x:x[3])
        for i,c in enumerate(cons): c.insert(0,i+1)
        # attach consensus to college stat rows (name match, skill positions)
        byk={c[8]:c for c in cons}
        for r in rows:
            c=byk.get(key(r[0])); r+= [c[0],c[4],c[5],c[6],c[7]] if c else [None]*5
            if c: r[31]='A+' if c[0]<=10 else 'A' if c[0]<=25 else 'A-' if c[0]<=50 else 'B+' if c[0]<=75 else 'B'
            elif r[11] is not False and r[31] in('A+','A','A-','B+'): r[31]='B'
        CB={'P':[c[:8]+c[9:] for c in cons],'S':[[s.source,s.url,s.updated,int(s.blen)] for _,s in srcs.iterrows()]}
        print('consensus ok:',len(cons),'players on 2+ boards from',len(srcs),'boards | top 8:',[(c[1],c[2],c[4]) for c in cons[:8]])
        print('consensus skill players matched to college stats:',sum(1 for r in rows if r[35]),'of',sum(1 for c in cons if c[2] in('QB','RB','WR','TE')))
        print('unmatched skill:',[c[1] for c in cons if c[2] in('QB','RB','WR','TE') and not any(len(r)>35 and r[35]==c[0] for r in rows)])
    else:
        for r in rows: r+=[None]*5
    CF={'P':rows,'draft':SEASON+1,'tg':bool(TGP),'CB':CB}
    top_=sorted(rows,key=lambda r:-r[30])[:5]; print('college top dynasty scores:',[(r[0],r[1],r[2],r[30],r[31]) for r in top_])
    print('college ok:',len(rows),'players | draft-eligible',sum(1 for x in rows if x[11]),'| with recruiting stars',sum(1 for x in rows if x[5]))
except Exception as ex:
    print('college data skipped:',ex)
names={t:N[t] for t in set(df.recent_team)}
def clean(o):
    if isinstance(o,float) and (o!=o or o in (float('inf'),float('-inf'))): return None
    if isinstance(o,dict): return {k:clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [clean(v) for v in o]
    if isinstance(o,(np.integer,)): return int(o)
    if isinstance(o,(np.floating,)): return clean(float(o))
    return o
IDS=set()
for pos in P:
    for row in P[pos]: pid=row.pop(); row.append(INJ.get(pid)); row.append(DLAB.get(pid)); f_=FORM.get(pid,[None,None]); s_=SNAP.get(pid,[None,None]); row.append([f_[0],f_[1],s_[0],s_[1]]); row.append(pid); IDS.add(pid)
for row in X: pid=row.pop(); row.append(INJ.get(pid)); row.append(DLAB.get(pid)); s_=SNAP.get(pid,[None,None]); row.append([None,None,s_[0],s_[1]]); row.append(pid); IDS.add(pid)
# ---- player card extras: photo, ESPN id, size, game log
PL={};LOG={}
try:
    if DY: IDS|={r[16] for r in DY['P'] if isinstance(r[16],str)}
    bio2=pl.drop_duplicates('gsis_id').set_index('gsis_id') if pl is not None else None
    if WK is not None:
        for pid,g in WK.sort_values('week').groupby('player_id'):
            LOG[pid]=[[int(r.week),r.opponent_team,round(float(r.fantasy_points_ppr),1),round(float(r.fantasy_points),1),int(r.yds),int(r.td),int(r.receptions),int(r.passing_yards),int(r.rushing_yards),int(r.receiving_yards),int(r.passing_tds),int(r.rushing_tds+r.receiving_tds)] for _,r in g.iterrows()]
    HS=df.drop_duplicates('player_id').set_index('player_id').headshot_url if 'headshot_url' in df else {}
    for g in IDS|set(LOG):
        b_=bio2.loc[g] if bio2 is not None and g in bio2.index else None
        hs=HS.get(g) if hasattr(HS,'get') else None
        if (hs is None or hs!=hs) and b_ is not None: hs=b_.get('headshot')
        PL[g]=[hs if isinstance(hs,str) else None,(str(int(float(b_['espn_id']))) if b_ is not None and pd.notna(b_.get('espn_id')) else None),
               (int(b_['height']) if b_ is not None and pd.notna(b_.get('height')) else None),(int(b_['weight']) if b_ is not None and pd.notna(b_.get('weight')) else None),
               (str(b_['birth_date'])[:10] if b_ is not None and pd.notna(b_.get('birth_date')) else None)]
    print('player cards ok:',len(PL),'players | with photo',sum(1 for v in PL.values() if v[0]),'| with ESPN id',sum(1 for v in PL.values() if v[1]),'| game logs',len(LOG))
except Exception as ex: print('player card extras failed:',ex)
print('tags: injured on lists',sum(1 for p in P for r in P[p] if r[5])+sum(1 for r in X if r[17]),'| with depth label',sum(1 for p in P for r in P[p] if r[6])+sum(1 for r in X if r[18]))
# ---- betting: lines and props (The Odds API, needs the ODDS_API_KEY secret)
ODD=None
try:
    import re as _re2, statistics as _st
    tset={t[0] for t in T}
    class _TeamMap(dict):
        def get(self,name,default=None):
            nick=str(name).split()[-1]
            for c_ in tset:
                if N.get(c_)==nick: return c_
            return default
    TM=_TeamMap()
    od,oinfo=sources.odds_update({(g_[0],g_[1]) for g_ in G},TM,'odds')
    META['sources']['odds']=oinfo
    BOOK={'pinnacle':'Pinnacle','draftkings':'DraftKings','fanduel':'FanDuel','betmgm':'BetMGM','betrivers':'BetRivers','bovada':'Bovada','betonlineag':'BetOnline','mybookieag':'MyBookie','lowvig':'LowVig','betus':'BetUS','williamhill_us':'Caesars','espnbet':'ESPN BET','fanatics':'Fanatics','ballybet':'Bally Bet','hardrockbet':'Hard Rock'}
    bk=lambda k:BOOK.get(k,k)
    def prob(a):
        a=float(a); return 100/(a+100) if a>0 else -a/(-a+100)
    dec=lambda a:(1+a/100) if a>0 else (1-100/a)
    def novig(p1,p2):
        """Chance of side 1 with the bookmaker's cut removed, Shin's method (it doesn't over-credit long shots the way a plain proportional split does)."""
        q=[prob(p1),prob(p2)]; S=sum(q)
        if S<=1: return q[0]/S
        pr_=lambda z:[((z*z+4*(1-z)*x*x/S)**.5-z)/(2*(1-z)) for x in q]
        lo,hi=0.0,0.4
        for _ in range(60):
            mid=(lo+hi)/2
            if sum(pr_(mid))>1: lo=mid
            else: hi=mid
        r=pr_((lo+hi)/2); return r[0]/sum(r)
    def mode(xs):
        xs=[x for x in xs if x is not None]
        return max(set(xs),key=lambda x:(xs.count(x),-abs(x-_st.median(xs)))) if xs else None
    med=lambda xs:(_st.median(xs) if xs else None)
    from math import erf,sqrt
    Phi=lambda x:.5*(1+erf(x/sqrt(2)))
    # ---- team model from game scores (nflverse schedule): ridge-regressed ratings, with half of last season as a prior
    sch=sources.load('schedule')[0]; sch=sch[sch.game_type=='REG'].copy()
    fx=lambda t:t if t in tset else ALIAS.get(t,t)
    sch['home_team']=sch.home_team.map(fx); sch['away_team']=sch.away_team.map(fx)
    def fit(g,prior=None,lam=8.0):
        tl=sorted(tset); ix={t:i for i,t in enumerate(tl)}; n=len(tl); Xm=[];ym=[];Xp=[];yp=[]
        for r in g.itertuples():
            if r.home_team not in ix or r.away_team not in ix: continue
            h,a=ix[r.home_team],ix[r.away_team]
            x=np.zeros(n+1);x[h]=1;x[a]=-1;x[n]=1;Xm.append(x);ym.append(r.home_score-r.away_score-((prior[r.home_team]-prior[r.away_team]) if prior else 0))
            for sc,o,dd,hm in ((r.home_score,h,a,1),(r.away_score,a,h,-1)):
                x=np.zeros(2*n+2);x[o]=1;x[n+dd]=-1;x[2*n]=1;x[2*n+1]=hm/2;Xp.append(x);yp.append(sc)
        rid=lambda X,y,pen:np.linalg.solve(np.array(X).T@np.array(X)+np.diag(pen),np.array(X).T@np.array(y))
        bm=rid(Xm,ym,np.r_[np.full(n,lam),.01]); bp_=rid(Xp,yp,np.r_[np.full(2*n,lam),.01,.01])
        R={t:bm[ix[t]]+(prior[t] if prior else 0) for t in tl}
        return R,bm[n],{t:bp_[ix[t]] for t in tl},{t:bp_[n+ix[t]] for t in tl},bp_[2*n]
    last=sch[(sch.season==SEASON-1)&sch.home_score.notna()]
    PRI={t:.5*v for t,v in fit(last)[0].items()} if len(last) else None
    cur=sch[(sch.season==SEASON)&sch.home_score.notna()]
    def proj(R,hfa,O,D_,mu,h,a):
        m=R[h]-R[a]+hfa; t=2*mu+O[h]+O[a]-D_[h]-D_[a]; return m,t
    # walk-forward record vs closing lines: weeks 4+, only when the model and the line differ by 2.5+ points
    MR={'w':0,'l':0,'p':0,'tw':0,'tl':0,'tp':0}
    for wk in sorted(cur.week.unique()):
        if wk<4: continue
        fm=fit(cur[cur.week<wk],PRI)
        for r in cur[cur.week==wk].itertuples():
            if r.home_team not in fm[0] or r.away_team not in fm[0] or pd.isna(r.spread_line): continue
            m,t=proj(*fm,r.home_team,r.away_team)
            if abs(m-r.spread_line)>=2.5:
                cv=(r.result-r.spread_line)*np.sign(m-r.spread_line); MR['w' if cv>0 else 'l' if cv<0 else 'p']+=1
            if not pd.isna(r.total_line) and abs(t-r.total_line)>=3:
                cv=(r.total-r.total_line)*np.sign(t-r.total_line); MR['tw' if cv>0 else 'tl' if cv<0 else 'tp']+=1
    FM=fit(cur,PRI)
    # team against-the-spread and over/under records this season (closing lines from nflverse)
    REC={t:{'ats':[0,0,0],'ou':[0,0,0],'pf':0,'pa':0,'g':0} for t in tset}
    for r in cur.itertuples():
        if pd.isna(r.spread_line): continue
        for tm_,sg in ((r.home_team,1),(r.away_team,-1)):
            if tm_ not in REC: continue
            c_=(r.result-r.spread_line)*sg; REC[tm_]['ats'][0 if c_>0 else 1 if c_<0 else 2]+=1
            if not pd.isna(r.total_line): o_=r.total-r.total_line; REC[tm_]['ou'][0 if o_>0 else 1 if o_<0 else 2]+=1
            REC[tm_]['pf']+=r.home_score if sg>0 else r.away_score; REC[tm_]['pa']+=r.away_score if sg>0 else r.home_score; REC[tm_]['g']+=1
    up=sch[(sch.season==SEASON)&sch.home_score.isna()]
    UPR={(r.away_team,r.home_team):r for r in up.itertuples()}
    # line history (one point per refresh), kept in odds/history.json
    hp='odds/history.json'
    try: HIST=json.load(open(hp))
    except Exception: HIST={}
    BKS={}
    GL=[]
    for ev in od['events']:
        a_,h_=TM.get(ev['away_team']),TM.get(ev['home_team'])
        if not a_ or not h_: continue
        bb={}
        for B in ev.get('bookmakers',[]):
            nm_=bk(B['key']); x={}
            for M in B.get('markets',[]):
                oc={(o.get('name')):o for o in M.get('outcomes',[])}
                if M['key']=='h2h' and ev['home_team'] in oc and ev['away_team'] in oc: x['m']=[oc[ev['home_team']]['price'],oc[ev['away_team']]['price']]
                elif M['key']=='spreads' and ev['home_team'] in oc and ev['away_team'] in oc: x['s']=[oc[ev['home_team']].get('point'),oc[ev['home_team']]['price'],oc[ev['away_team']].get('point'),oc[ev['away_team']]['price']]
                elif M['key']=='totals' and 'Over' in oc and 'Under' in oc: x['o']=[oc['Over'].get('point'),oc['Over']['price'],oc['Under']['price']]
            if x: bb[nm_]=x; BKS[nm_]=BKS.get(nm_,0)+1
        # fair odds: Pinnacle (the sharpest book) with its cut removed when it has the market, otherwise the middle of the other books
        fair={'ref':{}}; pin=bb.get('Pinnacle',{})
        for mk_,i1,i2 in (('s',1,3),('o',1,2)):
            if mk_ in pin and pin[mk_][0] is not None:
                fair[mk_]=[pin[mk_][0],round(novig(pin[mk_][i1],pin[mk_][i2]),4)]; fair['ref'][mk_]='Pinnacle'; continue
            pt0=mode([v[mk_][0] for v in bb.values() if mk_ in v])
            if pt0 is None: continue
            ps=[novig(v[mk_][i1],v[mk_][i2]) for v in bb.values() if mk_ in v and v[mk_][0]==pt0]
            fair[mk_]=[pt0,round(med(ps),4) if len(ps)>=3 else None]; fair['ref'][mk_]='market'
        if 'm' in pin: fair['m']=round(novig(pin['m'][0],pin['m'][1]),4); fair['ref']['m']='Pinnacle'
        else:
            pm=[novig(v['m'][0],v['m'][1]) for v in bb.values() if 'm' in v]
            if len(pm)>=3: fair['m']=round(med(pm),4); fair['ref']['m']='market'
        cons_s=mode([v['s'][0] for v in bb.values() if 's' in v]); cons_o=mode([v['o'][0] for v in bb.values() if 'o' in v])
        mod=None
        if h_ in FM[0] and a_ in FM[0]:
            m,t=proj(*FM,h_,a_); mod={'m':round(m,1),'t':round(t,1),'wp':round(Phi(m/13.5),3)}
        u=UPR.get((a_,h_)); ctx={'div':bool(u.div_game) if u is not None and not pd.isna(u.div_game) else False,
             'rest':[None if u is None or pd.isna(u.away_rest) else int(u.away_rest),None if u is None or pd.isna(u.home_rest) else int(u.home_rest)],
             'roof':(u.roof if u is not None and isinstance(u.roof,str) else None)}
        wk_=int(u.week) if u is not None else None
        if ctx['roof'] in (None,'outdoors') and h_ not in ('ATL','DET','MIN','NO','LV','LA','LAC','ARI','DAL','HOU','IND') and not os.environ.get('ODDS_OFFLINE') and (u is None or str(getattr(u,'location','Home'))!='Neutral'):
            try: ctx['wx']=sources.weather_at(h_,ev['commence_time'])
            except Exception as ex_: print('weather failed for',h_,ex_)
        for side,tm_ in (('a',a_),('h',h_)):
            r_=REC.get(tm_)
            if r_ and r_['g']: ctx[side]={'ats':r_['ats'],'ou':r_['ou'],'pf':round(r_['pf']/r_['g'],1),'pa':round(r_['pa']/r_['g'],1)}
        hist=HIST.get(ev['id'],[]); pt_=[oinfo['lines_at'][:16],cons_s,cons_o,fair.get('m')]
        if not os.environ.get('ODDS_OFFLINE') and (not hist or hist[-1][1:3]!=pt_[1:3] or hist[-1][0][:10]!=pt_[0][:10]): hist=(hist+[pt_])[-30:]
        HIST[ev['id']]=hist
        GL.append({'id':ev['id'],'wk':wk_,'a':a_,'h':h_,'t':ev['commence_time'],'b':bb,'fair':fair,'mod':mod,'ctx':ctx,'mv':[[x[0],x[1],x[2]] for x in hist]})
    if not os.environ.get('ODDS_OFFLINE'):
        live={g_['id'] for g_ in GL}; json.dump({k:v for k,v in HIST.items() if k in live},open(hp,'w'))
    # ---- props
    def nn(s): s=str(s).lower().replace('’',"'"); s=_re2.sub(r"[.,']",'',s); s=_re2.sub(r'\b(jr|sr|ii|iii|iv|v)\b','',s); return _re2.sub(r'\s+',' ',s).strip()
    who={}
    for pos_,rows_ in P.items():
        if pos_=='K': continue
        for r_ in rows_: who.setdefault(nn(r_[0]),[]).append((pos_,r_[1],r_[8]))
    MK={'player_pass_yds':('Pass yds',7),'player_rush_yds':('Rush yds',8),'player_reception_yds':('Rec yds',9),'player_receptions':('Receptions',6),'player_pass_tds':('Pass TDs',10),'player_anytime_td':('Anytime TD',11)}
    ALT={'Pass yds':2,'Rush yds':2,'Rec yds':2,'Receptions':4,'Pass TDs':3,'Anytime TD':3}
    LA={}
    if ALW:
        for p_ in ['QB','RB','WR','TE']:
            v_=[t_['a'][p_] for t_ in ALW['T'].values() if p_ in t_['a']]; LA[p_]=[sum(x[i] for x in v_)/len(v_) for i in range(5)]
    PR=[]
    for eid,pc in od['props'].items():
        ev=pc['data']; a_,h_=TM.get(ev.get('away_team','')),TM.get(ev.get('home_team',''))
        agg={}
        for B in ev.get('bookmakers',[]):
            nm_=bk(B['key'])
            for M in B.get('markets',[]):
                if M['key'] not in MK: continue
                for o in M.get('outcomes',[]):
                    d=agg.setdefault((o.get('description'),M['key']),{})
                    x=d.setdefault(nm_,[None,None,None,None]); pr,pt=o.get('price'),o.get('point')
                    if o.get('name')=='Over': x[0],x[1]=pt,pr
                    elif o.get('name')=='Under': x[2],x[3]=pt,pr
                    elif o.get('name')=='Yes': x[1]=pr
        for (desc,mk),d in agg.items():
            c_=[x for x in who.get(nn(desc),[]) if x[1] in (a_,h_)] or who.get(nn(desc),[])
            if not c_: continue
            pos_,tm_,gid=c_[0]; opp=h_ if tm_==a_ else a_
            lab,si=MK[mk]; lg_=LOG.get(gid,[])
            if not lg_: continue
            vals=[x[si] for x in lg_]
            avg=sum(vals)/len(vals); l3=sum(vals[-3:])/len(vals[-3:]); base=.6*avg+.4*l3
            ai=ALT[lab]; fac=1.0
            if ALW and opp in ALW['T'] and pos_ in ALW['T'][opp]['a'] and LA.get(pos_) and LA[pos_][ai]>0:
                fac=min(1.25,max(.8,1+.5*(ALW['T'][opp]['a'][pos_][ai]/LA[pos_][ai]-1)))
            d={k:v for k,v in d.items() if v[1] is not None}
            if not d: continue
            fair=None
            if mk=='player_anytime_td':
                impl=med([prob(v[1]) for v in d.values()]); sc=sum(1 for v in vals if v>=1)
                pj=round(min((sc+4*impl)/(len(vals)+4)*fac,.95),3)   # scoring rate, pulled toward the odds when the sample is small
            else:
                pj=round(base*fac,1)
                pt=mode([v[0] for v in d.values() if v[0] is not None and v[3] is not None])
                if pt is not None:
                    ps=[novig(v[1],v[3]) for v in d.values() if v[0]==pt and v[2]==pt and v[3] is not None]
                    if len(ps)>=3: fair=[pt,round(med(ps),4)]
            PR.append({'eid':eid,'ko':ev.get('commence_time'),'n':desc,'t':tm_,'pos':pos_,'gid':gid,'opp':opp,'mk':lab,'b':d,'fair':fair,'v':[[x[0],x[1],x[si]] for x in lg_],'avg':round(avg,1),'l3':round(l3,1),'pj':pj,'fac':round(fac,2)})
    pat=max([pc['fetched'] for pc in od['props'].values()],default=None)
    # ---- official picks (best price across books). The page uses the same rules for single-book views.
    RU={'val':[.025,.045,.07],'stale':.10,'mlmax':250,'mlmin':-300,'model':2.5,'minl':{'Pass yds':150,'Rush yds':25,'Rec yds':25,'Receptions':2.5,'Pass TDs':.5},'pick':2}
    valS=lambda v:0 if v is None else 3 if v>=RU['val'][2] else 2 if v>=RU['val'][1] else 1 if v>=RU['val'][0] else 0
    GSD={'hs':('s',0,1),'as':('s',2,3),'ov':('o',0,1),'un':('o',0,2),'mh':('m',None,0),'ma':('m',None,1)}
    def gq(g,k):
        m=GSD[k]; best=None
        for bn,x in g['b'].items():
            x=x.get(m[0])
            if not x or x[m[2]] is None: continue
            q={'pt':None if m[1] is None else x[m[1]],'pr':x[m[2]],'bk':bn}
            if best is None: best=q
            elif q['pt'] is not None and q['pt']!=best['pt']:
                if ((best['pt']-q['pt']) if k=='ov' else (q['pt']-best['pt']))>0: best=q
            elif q['pr']>best['pr']: best=q
        return best
    def gfair(g,k):
        f=g['fair']
        if k in('hs','as'):
            if not f.get('s') or f['s'][1] is None: return None
            return {'pt':f['s'][0] if k=='hs' else -f['s'][0],'p':f['s'][1] if k=='hs' else 1-f['s'][1],'sp':1}
        if k in('ov','un'):
            if not f.get('o') or f['o'][1] is None: return None
            return {'pt':f['o'][0],'p':f['o'][1] if k=='ov' else 1-f['o'][1],'ov':k=='ov'}
        return None if f.get('m') is None else {'pt':None,'p':f['m'] if k=='mh' else 1-f['m']}
    def gev(q,fr):
        if not q or not fr: return None
        p=fr['p']
        if fr['pt'] is not None and q['pt']!=fr['pt']:
            d=(fr['pt']-q['pt']) if fr.get('ov') else (q['pt']-fr['pt'])
            if abs(d)>2: return None
            p+=d/.5*(.02 if fr.get('sp') else .015)
            if fr.get('sp'):
                lo,hi=min(abs(q['pt']),abs(fr['pt'])),max(abs(q['pt']),abs(fr['pt']))
                if (lo<3<hi) or (lo<7<hi): p+=(.03 if d>0 else -.03)
        return p*dec(q['pr'])-1
    def gside(g,k):
        q=gq(g,k)
        if not q: return None
        v=gev(q,gfair(g,k)); vs=valS(v); me=None; ms=0; flag=None
        if v is not None and v>RU['stale']: vs=0; flag='stale'
        if k in('mh','ma') and (q['pr']>RU['mlmax'] or q['pr']<RU['mlmin']): vs=0; flag=flag or 'range'
        if g['mod'] and k in('hs','as'):
            me=(g['mod']['m'] if k=='hs' else -g['mod']['m'])+q['pt']; ms=1 if me>=RU['model'] else 0
        return {'k':k,'q':q,'v':v,'vs':vs,'me':me,'ms':ms,'s':vs+ms,'flag':flag}
    INJ={}
    for pos_,rows_ in P.items():
        for r_ in rows_:
            if r_[5] and r_[8]: INJ[r_[8]]=r_[5][0]
    hurt=lambda gid:INJ.get(gid) in ('Out','IR','Reserve','Doubtful')
    def pq(p,sd):
        best=None
        for bn,x in p['b'].items():
            q={'pt':x[2],'pr':x[3],'bk':bn} if sd=='u' else {'pt':x[0],'pr':x[1],'bk':bn}
            if q['pr'] is None or (sd!='y' and q['pt'] is None): continue
            if best is None: best=q
            elif q['pt']!=best['pt']:
                if (q['pt']>best['pt']) if sd=='u' else (q['pt']<best['pt']): best=q
            elif q['pr']>best['pr']: best=q
        return best
    def pa(p):
        n=len(p['v'])
        if p['mk']=='Anytime TD':
            q=pq(p,'y')
            if not q: return None
            im=prob(q['pr']); d=p['pj']-im; ls=(3 if d>=.24 else 2 if d>=.16 else 1) if (n>=5 and im<=.6 and d>=.10) else 0
            return {'sd':'y','q':q,'ls':ls,'vs':0,'v':None,'s':min(ls,2),'srt':d}
        def side(q,dr):
            if not q: return None
            e=(p['pj']-q['pt'])/max(q['pt'],1)*dr; h=sum(1 for v in p['v'] if (v[2]>q['pt'] if dr>0 else v[2]<q['pt']))/n
            ls=(3 if e>=.25 else 2 if e>=.17 else 1) if (n>=4 and q['pt']>=RU['minl'].get(p['mk'],0) and e>=.10 and h>=.55) else 0
            v=None
            if p['fair'] and p['fair'][0]==q['pt']: v=(p['fair'][1] if dr>0 else 1-p['fair'][1])*dec(q['pr'])-1
            vs=valS(v)
            if v is not None and v>RU['stale']: vs=0
            return {'sd':'o' if dr>0 else 'u','q':q,'ls':ls,'vs':vs,'v':v,'s':min(ls,2)+vs,'srt':abs(e)}  # a lean alone tops out at level II; III needs a good price too
        o,u=side(pq(p,'o'),1),side(pq(p,'u'),-1)
        if o and u: return u if u['s']>o['s'] else o
        return o or u
    nowu=datetime.datetime.now(datetime.timezone.utc)
    started=lambda iso:datetime.datetime.fromisoformat(iso.replace('Z','+00:00'))<=nowu
    PK=[]
    for g in GL:
        if started(g['t']): continue
        for a1,a2,mk_ in (('hs','as','spread'),('ov','un','total'),('mh','ma','ml')):
            x1,x2=gside(g,a1),gside(g,a2); x=(x2 if x1 and x2 and x2['s']>x1['s'] else (x1 or x2)) if (x1 or x2) else None
            if x and x['s']>=RU['pick']:
                q=x['q']; PK.append({'id':'g|%s|%s|%s'%(g['id'],mk_,x['k']),'k':'g','eid':g['id'],'wk':g['wk'],'t':g['t'],'a':g['a'],'h':g['h'],'mk':mk_,'sd':x['k'],'pt':q['pt'],'pr':q['pr'],'bk':q['bk'],'s':x['s'],'v':None if x['v'] is None else round(x['v'],4),'ms':x['ms'],'vs':x['vs'],'srt':x['s']+(x['v'] or 0)*5})
    WKOF={g['id']:g['wk'] for g in GL}
    for p in PR:
        if not p.get('ko') or started(p['ko']) or hurt(p['gid']): continue
        x=pa(p)
        if x and x['s']>=RU['pick']:
            q=x['q']; PK.append({'id':'p|%s|%s|%s|%s'%(p['eid'],p['gid'],p['mk'],x['sd']),'k':'p','eid':p['eid'],'wk':WKOF.get(p['eid']),'t':p['ko'],'n':p['n'],'gid':p['gid'],'tm':p['t'],'opp':p['opp'],'mk':p['mk'],'sd':x['sd'],'pt':q['pt'],'pr':q['pr'],'bk':q['bk'],'s':x['s'],'v':None if x['v'] is None else round(x['v'],4),'ls':x['ls'],'vs':x['vs'],'pj':p['pj'],'srt':x['s']+x['srt']+(x['v'] or 0)*5})
    PK.sort(key=lambda x:-x['srt'])
    # ---- pick log: a pick counts if it was a pick at the last refresh before kickoff; graded from final scores and weekly stats
    pkf='odds/picks.json'
    try: PLOG=json.load(open(pkf))
    except Exception: PLOG={}
    for k_ in [k_ for k_,r_ in PLOG.items() if r_.get('res') is None and not started(r_['t'])]: del PLOG[k_]
    for x in PK:
        r_={k:v for k,v in x.items() if k!='srt'}; r_['res']=None; r_['at']=oinfo['lines_at'][:16]; PLOG[x['id']]=r_
    SI={'Pass yds':7,'Rush yds':8,'Rec yds':9,'Receptions':6,'Pass TDs':10,'Anytime TD':11}
    logmax=max((r[0] for L_ in LOG.values() for r in L_),default=0)
    fin={}
    for r in cur.itertuples(): fin[(int(r.week),r.away_team,r.home_team)]=(r.away_score,r.home_score); fin[(int(r.week),r.home_team)]=fin[(int(r.week),r.away_team)]=(r.away_team,r.home_team,r.away_score,r.home_score)
    for r_ in PLOG.values():
        if r_.get('res') is not None or not started(r_['t']) or r_.get('wk') is None: continue
        if r_['k']=='g':
            sc=fin.get((r_['wk'],r_['a'],r_['h']))
            if not sc: continue
            asc,hsc=sc
            if r_['mk']=='spread': c_=((hsc-asc) if r_['sd']=='hs' else (asc-hsc))+r_['pt']
            elif r_['mk']=='total': c_=((asc+hsc)-r_['pt'])*(1 if r_['sd']=='ov' else -1)
            else: c_=(hsc-asc)*(1 if r_['sd']=='mh' else -1)
            r_['res']='W' if c_>0 else 'L' if c_<0 else 'P'; r_['fin']=[asc,hsc]
        else:
            gm=fin.get((r_['wk'],r_.get('tm')))
            if not gm or logmax<r_['wk']: continue
            row=[x for x in LOG.get(r_['gid'],[]) if x[0]==r_['wk']]
            if not row: r_['res']='V'; continue
            val=row[0][SI[r_['mk']]]; r_['val']=val
            if r_['sd']=='y': r_['res']='W' if val>=1 else 'L'
            else:
                c_=(val-r_['pt'])*(1 if r_['sd']=='o' else -1); r_['res']='W' if c_>0 else 'L' if c_<0 else 'P'
        r_['u']=round(dec(r_['pr'])-1,3) if r_['res']=='W' else -1 if r_['res']=='L' else 0
    if not os.environ.get('ODDS_OFFLINE'): json.dump(PLOG,open(pkf,'w'))
    def summ(rs):
        return {'w':sum(1 for r in rs if r.get('res')=='W'),'l':sum(1 for r in rs if r.get('res')=='L'),'p':sum(1 for r in rs if r.get('res') in('P','V')),'u':round(sum(r.get('u',0) or 0 for r in rs),2)}
    done=[r for r in PLOG.values() if r.get('res')]
    REC2={'all':summ(done),'g':summ([r for r in done if r['k']=='g']),'p':summ([r for r in done if r['k']=='p']),'s3':summ([r for r in done if r['s']>=3])}
    LGL=sorted(PLOG.values(),key=lambda r:r['t'],reverse=True)
    FIN=[[int(r.week),r.away_team,r.home_team,int(r.away_score),int(r.home_score)] for r in cur.itertuples()]
    order=['DraftKings','FanDuel','BetMGM','Caesars','ESPN BET','Fanatics','BetRivers','Hard Rock','Bovada','BetOnline','Pinnacle','LowVig','BetUS','MyBookie','Bally Bet']
    books=sorted(BKS,key=lambda k:(order.index(k) if k in order else 99,k))
    ODD={'G':GL,'P':PR,'books':books,'MR':MR,'PK':PK,'LG':LGL,'REC':REC2,'RU':RU,'FIN':FIN,'at':oinfo['lines_at'],'pat':pat,'left':oinfo['credits_left'],'plan':oinfo['plan']}
    print('odds ok: games',len(GL),'| props',len(PR),'| books',books,'| picks',len(PK),[(x.get('n') or x['h'],x['mk'],x['sd'],x['pr'],x['s']) for x in PK[:6]],'| log',len(PLOG),REC2['all'],'| model record',MR,'| credits used now',oinfo['credits_used_now'],'left',oinfo['credits_left'])
except Exception as ex:
    print('odds skipped:',ex)
META['built']=DATE
data=json.dumps(clean({'META':META,'P':P,'PC':PCout,'T':T,'TC':[list(x) for x in TC],'N':names,'X':X,'DEP':DEP,'PL':PL,'LOG':LOG,'OLP':OLP,'ALW':ALW,'DY':DY,'CF':CF,'ODD':ODD,'G':G}),separators=(',',':'),ensure_ascii=False,allow_nan=False)
open('data.json','w').write(data)
ver=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M')
html=open('template.html').read().replace('__VER__',ver).replace('__DATE__',DATE)
open('index.html','w').write(html)
print(n,'players | data.json',len(data),'bytes | index.html',len(html.encode()),'bytes')
