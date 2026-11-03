// Switching between the top-level sections (NFL, Fantasy, Betting).
function showSec(s){st.sec=s;[].forEach.call($('sec').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===s)});
  $('nflnav').hidden=s!=='nfl';['vp','vt','vn','vc'].forEach(function(id){$(id).hidden=s!=='nfl'||id!=='v'+st.v});$('sf').hidden=s!=='fan';$('sb').hidden=s!=='bet';[].forEach.call($('bnav').children,function(b){b.setAttribute('aria-pressed',b.dataset.s===s)});document.querySelector('main').classList.toggle('wide',s==='bet');
  if(s==='fan')fShow();if(s==='bet')renderB()}
