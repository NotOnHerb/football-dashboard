// The animated page background (night ocean, day grassland, snowy peak) and the scene and motion settings.
var SCENE=(function(){var s=null,m=null;try{s=localStorage.getItem('scene');m=localStorage.getItem('theme')}catch(e){}return s||(m==='light'?'grass':'ocean')})();
document.documentElement.setAttribute('data-theme',SCENE==='ocean'?'dark':'light');document.documentElement.setAttribute('data-scene',SCENE);
var MOTION=(function(){var v=null;try{v=localStorage.getItem('motion')}catch(e){}if(v)return v==='on';if(window.matchMedia&&matchMedia('(max-width: 600px)').matches)return false;return !(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)})();
function setScene(s){SCENE=s;document.documentElement.setAttribute('data-theme',s==='ocean'?'dark':'light');document.documentElement.setAttribute('data-scene',s);try{localStorage.setItem('scene',s)}catch(e){}var b=document.getElementById('scn');if(b)b.value=s;SC.reset()}
function setMotion(on){MOTION=on;try{localStorage.setItem('motion',on?'on':'off')}catch(e){}var b=document.getElementById('mot');if(b)b.textContent=on?'Motion on':'Motion off';SC.reset()}
// ---------------- animated scenes: night ocean, day grassland
var SC=(function(){
  var cv,cx,W,H,dpr,stars=[],blades=[],clouds=[],ranges=[],flakes=[],raf=0,last=0;
  function rnd(a,b){return a+Math.random()*(b-a)}
  function size(){dpr=Math.min(window.devicePixelRatio||1,2);W=innerWidth;H=innerHeight;cv.width=W*dpr;cv.height=H*dpr;cx.setTransform(dpr,0,0,dpr,0,0);build()}
  function build(){stars=[];for(var i=0;i<Math.round(W*H/5000);i++)stars.push({x:rnd(0,W),y:rnd(0,H*.55),r:rnd(.4,1.5),p:rnd(0,6.3),s:rnd(.5,2)});
    blades=[];var n=Math.min(900,Math.round(W*.8));for(var j=0;j<n;j++){var layer=j/n;blades.push({x:rnd(-20,W+20),l:layer,h:rnd(.12,.26)*H*(.55+layer*.65),w:rnd(1.5,3.5)*(.6+layer*.8),c:Math.floor(rnd(0,5)),ph:rnd(0,6.3)})}
    blades.sort(function(a,b){return a.l-b.l});
    clouds=[];for(var k=0;k<6;k++)clouds.push({x:rnd(-.2,1.1)*W,y:rnd(.06,.38)*H,s:rnd(.6,1.4),v:rnd(4,12)});
    ranges=[[.50,.30,'#c9dcef','#9fb9d6',22],[.60,.26,'#e6f0fa','#a7bfd9',14],[.74,.18,'#f7fbff','#b8cde3',9]].map(function(R){var pts=[],x=-40,y;while(x<W+40){y=H*R[0]-H*R[1]*Math.pow(Math.random(),1.6);pts.push([x,y]);x+=rnd(W/R[4]*.5,W/R[4]*1.4)}return {pts:pts,base:R[0],hi:R[2],lo:R[3]}});
    flakes=[];for(var f=0;f<Math.round(W*H/2600);f++)flakes.push({x:rnd(0,W),y:rnd(0,H),r:rnd(.6,2.6),vx:rnd(60,160),vy:rnd(20,70),p:rnd(0,6.3)})}
  function night(t){var hz=H*.56,g=cx.createLinearGradient(0,0,0,hz);g.addColorStop(0,'#020814');g.addColorStop(.7,'#0a1d38');g.addColorStop(1,'#163558');cx.fillStyle=g;cx.fillRect(0,0,W,hz);
    stars.forEach(function(s){var a=.5+.5*Math.sin(s.p+t*s.s);cx.globalAlpha=.35+.65*a;cx.fillStyle='#e8f1ff';cx.beginPath();cx.arc(s.x,s.y,s.r,0,6.283);cx.fill()});cx.globalAlpha=1;
    var mx=W>1000?W*.91:W*.78,my=H*.13,mr=Math.max(22,Math.min(W,H)*.045),mg=cx.createRadialGradient(mx,my,mr*.5,mx,my,mr*6);mg.addColorStop(0,'rgba(220,235,255,.35)');mg.addColorStop(1,'rgba(220,235,255,0)');cx.fillStyle=mg;cx.fillRect(mx-mr*6,my-mr*6,mr*12,mr*12);
    cx.fillStyle='#f4f7ff';cx.beginPath();cx.arc(mx,my,mr,0,6.283);cx.fill();cx.fillStyle='rgba(180,195,220,.35)';cx.beginPath();cx.arc(mx-mr*.3,my-mr*.2,mr*.22,0,6.283);cx.arc(mx+mr*.35,my+mr*.25,mr*.15,0,6.283);cx.fill();
    var sg=cx.createLinearGradient(0,hz,0,H);sg.addColorStop(0,'#0d2a4a');sg.addColorStop(1,'#020a16');cx.fillStyle=sg;cx.fillRect(0,hz,W,H-hz);
    for(var L=0;L<7;L++){var y0=hz+(H-hz)*(L/7)*(L/7)+4,amp=2+L*3.2,len=120+L*60,sp=(L%2?1:-1)*(8+L*5);cx.fillStyle='rgba('+(20+L*6)+','+(60+L*10)+','+(105+L*12)+','+(.25+L*.06)+')';cx.beginPath();cx.moveTo(0,H);
      for(var x=0;x<=W+10;x+=10)cx.lineTo(x,y0+amp*Math.sin((x+t*sp)/len*6.283)+amp*.5*Math.sin((x*1.7-t*sp*.6)/len*6.283));cx.lineTo(W,H);cx.fill()}
    for(var r=0;r<46;r++){var yy=hz+4+r*r*(H-hz)/2300,wd=(8+r*1.6)*(.6+.4*Math.sin(t*1.3+r*1.7)),off=Math.sin(t*.8+r)*r*.6;cx.fillStyle='rgba(235,242,255,'+(.55-r*.01)*(.55+.45*Math.sin(t*2.1+r*2.3))+')';cx.fillRect(mx-wd/2+off,yy,wd,1.6+r*.05)}}
  function day(t){var hz=H*.6,g=cx.createLinearGradient(0,0,0,hz);g.addColorStop(0,'#3d8fe0');g.addColorStop(.55,'#8cc8f5');g.addColorStop(1,'#f6ecd0');cx.fillStyle=g;cx.fillRect(0,0,W,H);
    var sx=W*.18,sy=H*.15,sr=Math.max(26,Math.min(W,H)*.05),sg=cx.createRadialGradient(sx,sy,sr*.4,sx,sy,sr*7);sg.addColorStop(0,'rgba(255,248,220,.9)');sg.addColorStop(.25,'rgba(255,240,190,.35)');sg.addColorStop(1,'rgba(255,240,190,0)');cx.fillStyle=sg;cx.fillRect(0,0,W,H*.7);
    cx.fillStyle='#fffbea';cx.beginPath();cx.arc(sx,sy,sr,0,6.283);cx.fill();
    clouds.forEach(function(c){var x=((c.x+t*c.v)%(W*1.4))-W*.2,y=c.y,s=c.s*Math.min(1,W/900)*60;cx.fillStyle='rgba(255,255,255,.85)';cx.beginPath();cx.ellipse(x,y,s*1.6,s*.55,0,0,6.283);cx.ellipse(x+s*.9,y-s*.25,s*1.1,s*.6,0,0,6.283);cx.ellipse(x-s*.9,y+s*.05,s*.9,s*.45,0,0,6.283);cx.fill()});
    [[hz-H*.05,'#7fae8a',.0013,.6],[hz,'#6c9c58',.002,1]].forEach(function(h){cx.fillStyle=h[1];cx.beginPath();cx.moveTo(0,H);for(var x=0;x<=W+10;x+=12)cx.lineTo(x,h[0]+Math.sin(x*h[2]*6.283+h[3])*H*.03);cx.lineTo(W,H);cx.fill()});
    var fg=cx.createLinearGradient(0,hz,0,H);fg.addColorStop(0,'#7d9e3e');fg.addColorStop(1,'#3d6a24');cx.fillStyle=fg;cx.fillRect(0,hz+H*.03,W,H);
    var C=['#9fbf4a','#86aa3c','#b9c86a','#6f9a34','#cdbb6a'];
    blades.forEach(function(b){var base=hz+H*.04+b.l*(H-hz)*.95,gust=Math.sin(t*.9+b.x*.004)*.6+Math.sin(t*2.3+b.x*.011+b.ph)*.25,bend=(.35+gust*.5)*b.h*.45,tipx=b.x+bend,tipy=base-b.h*(1-Math.abs(gust)*.08);
      cx.strokeStyle=C[b.c];cx.globalAlpha=.55+b.l*.45;cx.lineWidth=b.w;cx.lineCap='round';cx.beginPath();cx.moveTo(b.x,base);cx.quadraticCurveTo(b.x+bend*.15,base-b.h*.55,tipx,tipy);cx.stroke()});cx.globalAlpha=1}
  function snow(t){var g=cx.createLinearGradient(0,0,0,H*.75);g.addColorStop(0,'#1f6fd1');g.addColorStop(.55,'#86c2f2');g.addColorStop(1,'#eef7ff');cx.fillStyle=g;cx.fillRect(0,0,W,H);
    var sx=W*.82,sy=H*.12,sr=Math.max(22,Math.min(W,H)*.04),sg=cx.createRadialGradient(sx,sy,sr*.3,sx,sy,sr*8);sg.addColorStop(0,'rgba(255,255,255,.95)');sg.addColorStop(.2,'rgba(255,250,235,.45)');sg.addColorStop(1,'rgba(255,250,235,0)');cx.fillStyle=sg;cx.fillRect(0,0,W,H*.6);
    cx.fillStyle='#ffffff';cx.beginPath();cx.arc(sx,sy,sr,0,6.283);cx.fill();
    ranges.forEach(function(R,ri){var gr=cx.createLinearGradient(0,H*(R.base-.32),0,H*R.base+40);gr.addColorStop(0,R.hi);gr.addColorStop(1,R.lo);cx.fillStyle=gr;cx.beginPath();cx.moveTo(-40,H);R.pts.forEach(function(p){cx.lineTo(p[0],p[1])});cx.lineTo(W+40,H);cx.fill();
      cx.fillStyle='rgba(70,100,140,'+(.16-ri*.03)+')';for(var i=1;i<R.pts.length-1;i++){var p=R.pts[i],q=R.pts[i+1];if(p[1]<q[1]){cx.beginPath();cx.moveTo(p[0],p[1]);cx.lineTo(q[0],q[1]);cx.lineTo(p[0]+(q[0]-p[0])*.35,H*R.base+30);cx.fill()}}
      if(ri===1)R.pts.forEach(function(p,i){if(i%2)return;var a=.25+.2*Math.sin(t*1.7+i);var sp=cx.createLinearGradient(p[0],p[1],p[0]+90,p[1]-14);sp.addColorStop(0,'rgba(255,255,255,'+a+')');sp.addColorStop(1,'rgba(255,255,255,0)');cx.fillStyle=sp;cx.beginPath();cx.ellipse(p[0]+40+((t*30+i*17)%30),p[1]-6,48,6,-.15,0,6.283);cx.fill()})});
    var fg=cx.createLinearGradient(0,H*.8,0,H);fg.addColorStop(0,'#f4f9ff');fg.addColorStop(1,'#dbe8f6');cx.fillStyle=fg;cx.beginPath();cx.moveTo(0,H);for(var x=0;x<=W+10;x+=14)cx.lineTo(x,H*.86+Math.sin(x*.004)*H*.025+Math.sin(x*.013)*H*.008);cx.lineTo(W,H);cx.fill();
    var gust=1+.6*Math.sin(t*.7);cx.fillStyle='#ffffff';
    flakes.forEach(function(f){var x=((f.x+t*f.vx*gust)%(W+40)+W+40)%(W+40)-20,y=((f.y+t*f.vy+Math.sin(t*2+f.p)*12)%(H+20)+H+20)%(H+20)-10;cx.globalAlpha=.45+f.r*.2;cx.beginPath();cx.ellipse(x,y,f.r*(1+gust*.6),f.r*.8,.12,0,6.283);cx.fill()});cx.globalAlpha=1}
  function frame(ms){raf=0;var t=ms/1000;if(MOTION&&ms-last<30){raf=requestAnimationFrame(frame);return}last=ms;
    ({ocean:night,grass:day,snow:snow}[SCENE]||night)(MOTION?t:12);if(MOTION&&!document.hidden)raf=requestAnimationFrame(frame)}
  function reset(){if(!cv)return;if(raf)cancelAnimationFrame(raf);raf=requestAnimationFrame(frame)}
  function init(){cv=document.getElementById('scene');if(!cv||!cv.getContext)return;cx=cv.getContext('2d');size();var rt_;addEventListener('resize',function(){clearTimeout(rt_);rt_=setTimeout(function(){size();reset()},150)});document.addEventListener('visibilitychange',reset);reset()}
  return {init:init,reset:reset}})();
document.addEventListener('DOMContentLoaded',function(){SC.init();var b=document.getElementById('scn');setScene(SCENE);b.onchange=function(){setScene(this.value)};var m=document.getElementById('mot');setMotion(MOTION);m.onclick=function(){setMotion(!MOTION)}});
