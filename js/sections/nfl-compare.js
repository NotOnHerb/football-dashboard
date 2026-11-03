// NFL -> Compare: two players at one position, category by category. Data: P, PC.
var CP={pos:'QB',a:null,b:null},LOWER=['INT','Sack %','Fum lost'];
function cList(){return A.filter(function(r){return r[2]===CP.pos}).sort(function(x,y){return y[4]*y[3]-x[4]*x[3]})}
function cLab(r){return r[0]+' ('+r[1]+')'}
function cSetup(){var l=cList();CP.a=l[0];CP.b=l[1];$('cl').innerHTML=l.map(function(r){return '<option value="'+cLab(r)+'">'}).join('');$('ca').value=cLab(l[0]);$('cb').value=cLab(l[1]);cRender()}
function cPick(k,el){var r=cList().filter(function(x){return cLab(x)===el.value})[0];if(r){CP[k]=r;cRender()}}
function cRender(){
  $('ia').innerHTML=CP.a?CP.a[1]+' · '+CP.a[3]+' GP'+tags(CP.a):'';$('ib').innerHTML=CP.b?CP.b[1]+' · '+CP.b[3]+' GP'+tags(CP.b):'';
  var a=CP.a,b=CP.b,wa=0,wb=0,rows='';
  D.PC[CP.pos].forEach(function(s,k){var x=a[4+k],y=b[4+k];if(x==null&&y==null)return;
    var low=LOWER.indexOf(s[0])>-1,nul=x==null||y==null,aw=(nul||x===y)?0:((low?x<y:x>y)?1:-1),sh=.5;
    if(aw===1)wa++;else if(aw===-1)wb++;
    if(!nul&&x!==y){var lo=Math.min(x,y),up=Math.max(x,y);sh=((x-lo)+.5*(up-lo))/(2*(up-lo));if(low)sh=1-sh}
    if(k===0)rows+='<div class="sec">The box score</div>';if(k===5)rows+='<div class="sec">Under the hood</div>';
    rows+='<div class="row '+(aw===1?'wa':aw===-1?'wb':'')+'"><div class="lbl">'+s[0]+(low?' (lower is better)':'')+'</div><div class="line"><span class="cv a '+(aw===1?'win':'')+'">'+f(x,s[1])+'</span><div class="field" role="img" aria-label="'+s[0]+': '+a[0]+' '+f(x,s[1])+', '+b[0]+' '+f(y,s[1])+'"><div class="fa" style="flex:'+sh.toFixed(3)+'"></div><div class="fb" style="flex:'+(1-sh).toFixed(3)+'"></div></div><span class="cv b '+(aw===-1?'win':'')+'">'+f(y,s[1])+'</span></div></div>';
  });
  $('cr').innerHTML=rows;
  $('cv').textContent=a===b?'Pick two different players':wa===wb?'Dead even: '+wa+' categories each':(wa>wb?a[0]:b[0])+' wins '+Math.max(wa,wb)+' of '+(wa+wb)+' decided categories';
  $('ct').innerHTML='<i class="a" style="flex:'+wa+'"></i><i class="b" style="flex:'+wb+'"></i>';
}
function cInit(){
  $('cpos').innerHTML=['QB','RB','WR','TE'].map(function(p){return '<button data-p="'+p+'" aria-pressed="'+(p==='QB')+'">'+p+'</button>'}).join('');
  $('cpos').addEventListener('click',function(e){var p=e.target.dataset.p;if(!p)return;CP.pos=p;[].forEach.call($('cpos').children,function(x){x.setAttribute('aria-pressed',x.dataset.p===p)});cSetup()});
  $('ca').oninput=function(){cPick('a',this)};$('cb').oninput=function(){cPick('b',this)};
  cSetup();
}
