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
def load_allowed():
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
        tot_a=sum(v['a'][p][0]*v['g'] for v in out.values() for p in v['a']); tot_s=sum(v['s'][p][0]*v['g'] for v in out.values() for p in v['s'])
        print('allowed ok: weeks',int(w.week.min()),'-',int(w.week.max()),'| teams',len(out),'| PPR allowed',round(tot_a),'vs scored',round(tot_s))
        return {'wk':int(w.week.max()),'T':out}
    except Exception as ex:
        print('weekly stats fetch failed, skill matchups hidden:',ex); return None
ALW=load_allowed()
names={t:N[t] for t in set(df.recent_team)}
def clean(o):
    if isinstance(o,float) and (o!=o or o in (float('inf'),float('-inf'))): return None
    if isinstance(o,dict): return {k:clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [clean(v) for v in o]
    if isinstance(o,(np.integer,)): return int(o)
    if isinstance(o,(np.floating,)): return clean(float(o))
    return o
for pos in P:
    for row in P[pos]: pid=row.pop(); row.append(INJ.get(pid)); row.append(DLAB.get(pid))
for row in X: pid=row.pop(); row.append(INJ.get(pid)); row.append(DLAB.get(pid))
print('tags: injured on lists',sum(1 for p in P for r in P[p] if r[5])+sum(1 for r in X if r[17]),'| with depth label',sum(1 for p in P for r in P[p] if r[6])+sum(1 for r in X if r[18]))
META['built']=DATE
data=json.dumps(clean({'META':META,'P':P,'PC':PCout,'T':T,'TC':[list(x) for x in TC],'N':names,'X':X,'DEP':DEP,'OLP':OLP,'ALW':ALW,'G':G}),separators=(',',':'),ensure_ascii=False,allow_nan=False)
open('data.json','w').write(data)
ver=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M')
html=open('template.html').read().replace('__VER__',ver).replace('__DATE__',DATE)
open('index.html','w').write(html)
print(n,'players | data.json',len(data),'bytes | index.html',len(html.encode()),'bytes')
