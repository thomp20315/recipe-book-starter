#!/usr/bin/env python3
"""Builds index.html, manifest.webmanifest, sw.js and icons/ from recipes.json + config.json. Run: python3 build.py"""
import json, html, os
CFG = json.load(open('config.json' if os.path.exists('config.json') else 'config.example.json'))
R = json.load(open('recipes.json'))
R = [r for _, r in sorted(enumerate(R), key=lambda p: (p[1].get('added') or '', p[0]), reverse=True)]  # newest first
e = html.escape
SB_URL = CFG["supabase_url"].rstrip("/")
SB_KEY = CFG["supabase_publishable_key"]  # public publishable key (safe in the site; RLS policies in supabase.sql)
if "YOUR-" in SB_URL or "YOUR-" in SB_KEY:
    print("NOTE: config.json still has placeholder Supabase values; the app builds but can't save anything yet (README step 2).")
RATERS = [(str(x["id"]), str(x["label"])) for x in CFG.get("raters") or []] or [("p1", "Person 1")]
RIDS = [w for w, _ in RATERS]
FAMILY = CFG.get("family_name") or ""
APP_NAME = CFG.get("app_name") or "Recipe Book"
SHORT_NAME = CFG.get("short_name") or "Recipes"
import re as _re
HIDE_WORDS = [w for w in (CFG.get("store_name_words_to_hide") or []) if w]
HIDE_RE = ("/ (" + "|".join(_re.escape(w).replace("/", "\\/") for w in HIDE_WORDS) + ")/g") if HIDE_WORDS else "/(?!)/g"
STORE_CARTS = {str(x["id"]).lower(): x.get("cart_url") for x in CFG.get("stores") or [] if x.get("id") and x.get("cart_url")}
SB_JS = """<script>
window.SB=function(path,o){o=o||{};var h={'apikey':%s,'Content-Type':'application/json'};if(o.prefer)h.Prefer=o.prefer;
var u=%s+'/rest/v1/'+path;return fetch(u,{method:o.method||'GET',headers:h,body:o.body?JSON.stringify(o.body):undefined,cache:'no-store'})
.then(function(r){if(!r.ok)return r.text().then(function(t){throw new Error(r.status+' '+t)});return r.status===204?null:r.text().then(function(t){return t?JSON.parse(t):null});});};
</script>""" % (json.dumps(SB_KEY), json.dumps(SB_URL))
ICON = {
 "cart": '<path d="M2.5 3.5h2.2l2.1 11.2a1.6 1.6 0 0 0 1.6 1.3h8.7a1.6 1.6 0 0 0 1.6-1.2l1.6-7.3H6"/><circle cx="9" cy="20" r="1.3"/><circle cx="17.5" cy="20" r="1.3"/>',
 "plus": '<path d="M12 5v14M5 12h14"/>',
 "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 4.5 4.5"/>',
 "close": '<path d="M6 6l12 12M18 6 6 18"/>',
 "star": '<path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z"/>',
 "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
 "back": '<path d="M15 5l-7 7 7 7"/>',
 "pencil": '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
 "trash": '<path d="M4 7h16M9.5 7V4.8h5V7M6.5 7l.9 12.2a1.5 1.5 0 0 0 1.5 1.3h6.2a1.5 1.5 0 0 0 1.5-1.3L17.5 7M10 11v6M14 11v6"/>',
 "leaf": '<path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14"/><path d="M5 19c3-4 6-6 9-8"/>',
 "tag": '<path d="M3.5 12.3V4.5a1 1 0 0 1 1-1h7.8l8.2 8.2a1.4 1.4 0 0 1 0 2l-6.8 6.8a1.4 1.4 0 0 1-2 0z"/><circle cx="8" cy="8" r="1.3"/>',
 "bag": '<path d="M5 8h14l-1 12.5H6z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/>',
 "dish": '<path d="M3 15h18M5 15a7 7 0 0 1 14 0M12 6V4.5M4 18.5h16"/>',
}
def ic(n, extra=""): return f'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"{extra}>{ICON[n]}</svg>'
KNOWN_TAGS = [t for t in CFG.get("tags") or [] if isinstance(t, str) and t.strip()]
def tags_of(r): return [t for t in (r.get("tags") or []) if isinstance(t, str) and t.strip()]
def chips(r): return ''.join(f'<span class="chip">{e(t)}</span>' for t in tags_of(r))
RATE_ROWS = "".join(f'<div class="rrow" data-who="{w}"><div class="rhead"><span class="who">{lbl}</span><span class="rval"></span></div><div class="pills" role="group" aria-label="{lbl} score">' + "".join(f'<button type="button" class="pill" data-v="{v}" aria-label="{lbl} {v} out of 10">{v}</button>' for v in range(1, 11)) + '</div></div>' for w, lbl in ((e(a), e(b)) for a, b in RATERS))
RATE_JS = ("""<script>
(function(){
var data={},busy=false,STAR=%s,RIDS=%s;
function avg(r){var v=RIDS.map(function(k){return r&&r[k]}).filter(function(x){return x>=1&&x<=10});return v.length?(v.reduce(function(a,b){return a+b},0)/v.length):null;}
function render(){document.querySelectorAll('.badge').forEach(function(b){var a=avg(data[b.dataset.rid]);if(a){b.textContent=a.toFixed(1)+'/10';b.hidden=false}else b.hidden=true;});
document.querySelectorAll('.ratings').forEach(function(box){var r=data[box.dataset.rid]||{};box.querySelectorAll('.rrow').forEach(function(row){var v=r[row.dataset.who]||0;
row.querySelectorAll('.pill').forEach(function(s){s.classList.toggle('on',+s.dataset.v===v);s.classList.toggle('lit',+s.dataset.v<v)});var rv=row.querySelector('.rval');if(rv)rv.textContent=v?v+'/10':'\u2014';});});}
function load(){return SB('ratings?select=recipe_id,person,score').then(function(rows){var d={};rows.forEach(function(x){(d[x.recipe_id]=d[x.recipe_id]||{})[x.person]=x.score});data=d;window.rbRatings=d;render();if(window.rbSearch)window.rbSearch();});}
function setv(rid,who,v){window.rbRatings=data;setTimeout(function(){if(window.rbSearch)window.rbSearch()},0);data[rid]=data[rid]||{};if(v)data[rid][who]=v;else{delete data[rid][who];if(!Object.keys(data[rid]).length)delete data[rid];}}
function msg(box,t){var m=box.querySelector('.rmsg');if(m)m.textContent=t;}
document.addEventListener('click',function(e){var s=e.target.closest('.pill');if(!s)return;e.preventDefault();var box=s.closest('.ratings'),rid=box.dataset.rid,who=s.closest('.rrow').dataset.who,
cur=(data[rid]||{})[who]||0,v=+s.dataset.v;if(v&&v===cur)v=0;
if(busy)return;busy=true;var prev=JSON.parse(JSON.stringify(data));setv(rid,who,v);render();msg(box,'Saving\\u2026');
var q=v?SB('ratings?on_conflict=recipe_id,person',{method:'POST',prefer:'resolution=merge-duplicates,return=minimal',body:{recipe_id:rid,person:who,score:v}})
:SB('ratings?recipe_id=eq.'+encodeURIComponent(rid)+'&person=eq.'+who,{method:'DELETE'});
q.then(function(){msg(box,v?'Saved \\u2713':'Cleared \\u2713');busy=false;load().catch(function(){});}).catch(function(){data=prev;render();msg(box,'Could not save \\u2014 check your connection and try again.');})
.then(function(){busy=false;});});
load().catch(function(){});setInterval(function(){if(!document.hidden)load().catch(function(){})},30000);
document.addEventListener('visibilitychange',function(){if(!document.hidden)load().catch(function(){});});
})();
</script>""" % (json.dumps(ic("star")), json.dumps(RIDS)))
# All styling lives in design.css (inlined at build time).
def img(r, cls):
    if r.get("image"):
        return f'<img class="{cls} fade" src="{e(r["image"])}" alt="" loading="lazy" decoding="async" onload="this.classList.add(\'in\')">'
    return f'<div class="ph {cls}">{ic("dish")}</div>'
import unicodedata
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
def stext(r): return norm(' '.join([r.get('title') or '', ' '.join(r.get('ingredients') or []), r.get('sourceName') or '', r.get('source') or '', r.get('addedBy') or '', ' '.join(tags_of(r))]))
def cmeta(r): return ' \u00b7 '.join(x for x in [f"Serves {r['servings']}" if r.get('servings') else '', str(r.get('totalTime') or r.get('cookTime') or '')] if x)
cards = ''.join(f'<a class="card" data-a="{e(r['title'].lower())}" data-s="{e(stext(r))}" data-t="{e('|' + '|'.join(norm(t) for t in tags_of(r)) + '|' if tags_of(r) else '')}" href="#{e(r["id"])}">{img(r,"")}<span class="badge" data-rid="{e(r["id"])}" hidden></span><div class="ct"><h3>{e(r["title"])}</h3><p class="cm">{e(cmeta(r))}</p><div class="tags" data-rid="{e(r["id"])}">{chips(r)}</div></div></a>' for r in R)
pages = ''
for r in R:
    meta = ''.join(f'<span><b>{k}</b> {e(str(r[f]))}</span>' for k, f in
                   [('Serves', 'servings'), ('Prep', 'prepTime'), ('Cook', 'cookTime'), ('Total', 'totalTime')] if r.get(f))
    ing = ''.join(f'<li>{e(i)}</li>' for i in r['ingredients'])
    st = ''.join(f'<li>{e(s)}</li>' for s in r['steps'])
    pages += f'''<section class="recipe" id="{e(r["id"])}"><a class="back" href="#">All recipes</a>
<div class="imgwrap">{img(r,"hero")}<span class="badge" data-rid="{e(r["id"])}" hidden></span></div><div class="rbody"><h2>{e(r["title"])}</h2><p class="desc">{e(r.get("description",""))}</p>
<div class="meta">{meta}</div><div class="rtags" data-rid="{e(r["id"])}"><div class="chips">{chips(r)}</div></div><button type="button" class="cartadd" data-rid="{e(r["id"])}">{ic("cart")}Add to Cart</button><div class="ratings" data-rid="{e(r["id"])}"><h4>Family ratings</h4>{RATE_ROWS}<p class="rmsg"></p></div><div class="cols"><div><h4>Ingredients</h4><ul>{ing}</ul></div>
<div><h4>Steps</h4><ol>{st}</ol></div></div>
<p class="src">Source: <a href="{e(r["source"])}" target="_blank" rel="noopener">{e(r.get("sourceName", r["source"]))}</a>{(' &middot; <a href="' + e(r["sourcePost"]) + '" target="_blank" rel="noopener">Original post</a>') if r.get("sourcePost") else ''}</p></div></section>'''
SEARCH_JS = """<script>
(function(){var q=document.getElementById('q'),x=document.getElementById('qx'),nm=document.getElementById('nomatch'),nmq=document.getElementById('nmq'),cards=[].slice.call(document.querySelectorAll('.card'));
function norm(s){return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');}
function run(){var raw=q.value,w=norm(raw).split(/\\s+/).filter(Boolean),n=0,ft=window.rbTag?norm(window.rbTag):'';
cards.forEach(function(c){var ok=w.every(function(t){return c.dataset.s.indexOf(t)>=0})&&(!ft||(' '+(c.dataset.t||'')+' ').indexOf('|'+ft+'|')>=0)&&(!window.rbRateOk||window.rbRateOk(c));c.classList.toggle('hide',!ok);if(ok)n++;});
x.hidden=!raw;var rl=window.rbRateLbl?window.rbRateLbl():'',sub=document.querySelector('.intro .sub');if(sub)sub.textContent=(n===cards.length?n:n+' of '+cards.length)+' recipes';if(window.rbSort)window.rbSort(cards);
nm.hidden=n>0||!cards.length;if(!n&&rl&&!raw.trim()&&!ft){nm.textContent=rl==='Unrated'?'Every recipe has been rated.':'No recipes rated '+rl+' yet.';}else{nm.innerHTML='No recipes match \u201c<span id="nmq"></span>\u201d. Try another word.';nmq=document.getElementById('nmq');nmq.textContent=[raw.trim(),ft?window.rbTag:'',rl?'Rating '+rl:''].filter(Boolean).join(' + ');}}window.rbSearch=run;
q.addEventListener('input',run);x.addEventListener('click',function(){q.value='';run();q.focus();});
q.addEventListener('keydown',function(e){if(e.key==='Escape'){q.value='';run();}if(e.key==='Enter')q.blur();});run();})();
</script>"""
RATEF_JS = ("""<script>
(function(){var RATERS=%s,K='rbRateF',st={min:'',who:'all',sort:''};try{st=Object.assign(st,JSON.parse(sessionStorage.getItem(K)||'{}'))}catch(e){}
var chip=document.getElementById('rateChip'),pk=document.getElementById('ratePick'),grid=document.querySelector('.grid'),W={all:'Everyone'};RATERS.forEach(function(x){W[x[0]]=x[1]});if(st.who!=='all'&&!W[st.who])st.who='all';
function sc(rid){var r=(window.rbRatings||{})[rid];if(!r)return null;var ks=st.who==='all'?RATERS.map(function(x){return x[0]}):[st.who],v=ks.map(function(k){return r[k]}).filter(function(x){return x>=1&&x<=10});return v.length?v.reduce(function(a,b){return a+b},0)/v.length:null;}
function rid(c){return c.getAttribute('href').slice(1)}
window.rbRateOk=function(c){if(!st.min)return true;var a=sc(rid(c));return st.min==='u'?a==null:(a!=null&&a>=+st.min);};
window.rbRateLbl=function(){if(!st.min)return '';var w=st.who==='all'?'':W[st.who]+' ';return st.min==='u'?(w?w+'unrated':'Unrated'):w+st.min+'+';};
window.rbSort=function(cards){cards.forEach(function(c,i){if(c.dataset.i==null)c.dataset.i=i});var o=cards.slice();if(st.sort==='top')o.sort(function(a,b){var x=sc(rid(a)),y=sc(rid(b));return (y==null?-1:y)-(x==null?-1:x)||a.dataset.i-b.dataset.i});else if(st.sort==='az')o.sort(function(a,b){return a.dataset.a.replace(/^[^a-z0-9]+/,'').localeCompare(b.dataset.a.replace(/^[^a-z0-9]+/,''))||a.dataset.i-b.dataset.i});else o.sort(function(a,b){return a.dataset.i-b.dataset.i});
var cur=[].slice.call(grid.children);if(o.some(function(c,i){return cur[i]!==c}))o.forEach(function(c){grid.appendChild(c)});};
function seg(k,opts){return '<div class="rseg" role="radiogroup">'+opts.map(function(o){return '<button type="button" role="radio" aria-checked="'+(st[k]===o[0])+'" class="'+(st[k]===o[0]?'on':'')+'" data-k="'+k+'" data-v="'+o[0]+'">'+o[1]+'</button>'}).join('')+'</div>';}
function paint(){var l=window.rbRateLbl();chip.innerHTML=(l?'Rating '+l:'Rating')+(st.sort==='top'?' \\u00b7 Top':st.sort==='az'?' \\u00b7 A\\u2013Z':'')+'<span class="chev" aria-hidden="true"></span>';chip.classList.toggle('on',!!(l||st.sort));chip.setAttribute('aria-expanded',!pk.hidden);
pk.innerHTML='<p class="rpl">Minimum score</p>'+seg('min',[['','Any'],['9','9+'],['8','8+'],['7','7+'],['6','6+'],['u','Unrated']])+'<p class="rpl">Rated by</p>'+seg('who',[['all','Everyone']].concat(RATERS))+'<p class="rpl">Sort</p>'+seg('sort',[['','Newest'],['top','Highest rated'],['az','A\\u2013Z']]);
try{sessionStorage.setItem(K,JSON.stringify(st))}catch(e){}if(window.rbSearch)window.rbSearch();}
chip.addEventListener('click',function(){pk.hidden=!pk.hidden;paint();});
pk.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;st[b.dataset.k]=b.dataset.v;paint();});
document.addEventListener('click',function(e){if(!pk.hidden&&e.target.isConnected&&!e.target.closest('#ratePick,#rateChip')){pk.hidden=true;paint();}});
paint();})();
</script>""" % json.dumps([list(x) for x in RATERS]))
TAGS_JS = ("""<script>
(function(){
var KT=%s,BASE=%s,cur={},ok=true,$$=function(q){return [].slice.call(document.querySelectorAll(q))};
function norm(s){return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');}
function esc(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function canon(t){t=String(t||'').trim().replace(/ +/g,' ').slice(0,40);var k=KT.filter(function(x){return x.toLowerCase()===t.toLowerCase()})[0];return k||t;}
function tags(rid){return cur[rid]||BASE[rid]||[];}
var cards=$$('.card');cards.forEach(function(c){c.dataset.b=c.dataset.s.replace(/ [^ ]*$/,'')===c.dataset.s?c.dataset.s:c.dataset.s;});
function renderAll(){var used={};
$$('.tags').forEach(function(el){var t=tags(el.dataset.rid);t.forEach(function(x){used[x]=1});el.innerHTML=t.map(function(x){return '<span class="chip">'+esc(x)+'</span>'}).join('');});
cards.forEach(function(c){var rid=c.getAttribute('href').slice(1),t=tags(rid),base=c.dataset.base||(c.dataset.base=c.dataset.s.replace(/\u0001.*$/,''));
c.dataset.s=base+'\u0001 '+norm(t.join(' '));c.dataset.t=t.length?'|'+t.map(norm).join('|')+'|':'';});
$$('.rtags').forEach(renderEd);
var bar=document.getElementById('tagBar'),list=KT.filter(function(x){return used[x]}).concat(Object.keys(used).filter(function(x){return KT.indexOf(x)<0}).sort());
if(window.rbTag&&!used[window.rbTag])window.rbTag='';
bar.hidden=!list.length;bar.innerHTML=list.map(function(x){return '<button type="button" class="chip'+(window.rbTag===x?' on':'')+'" data-t="'+esc(x)+'">'+esc(x)+'</button>'}).join('');
if(window.rbSearch)window.rbSearch();}
function renderEd(box){var rid=box.dataset.rid,t=tags(rid),open=box.classList.contains('adding');
var h='<div class="chips">'+t.map(function(x){return '<button type="button" class="chip ed" data-t="'+esc(x)+'" aria-label="Remove tag '+esc(x)+'">'+esc(x)+'<span aria-hidden="true">&times;</span></button>'}).join('')+
'<button type="button" class="chip add" aria-expanded="'+open+'">+ Tag</button></div>';
if(open){h+='<div class="tagmenu">'+KT.filter(function(x){return t.indexOf(x)<0}).map(function(x){return '<button type="button" class="chip" data-add="'+esc(x)+'">'+esc(x)+'</button>'}).join('')+
'<form class="tagnew"><input type="text" maxlength="40" placeholder="Custom tag" autocomplete="off" enterkeyhint="done"><button type="submit">Add</button></form></div>';}
h+='<p class="tmsg"></p>';box.innerHTML=h;}
function save(box,next){var rid=box.dataset.rid,prev=cur[rid];cur[rid]=next;renderAll();var m=box.querySelector('.tmsg');
if(!ok){if(m)m.textContent='Tags need a one-time database setup (recipe_tags) before they can be saved.';cur[rid]=prev;setTimeout(renderAll,2500);return;}
SB('recipe_tags?on_conflict=recipe_id',{method:'POST',prefer:'resolution=merge-duplicates,return=minimal',body:{recipe_id:rid,tags:next}})
.then(function(){var m=box.querySelector('.tmsg');if(m){m.textContent='Saved \u2713';setTimeout(function(){if(m)m.textContent=''},1500);}})
.catch(function(){if(prev===undefined)delete cur[rid];else cur[rid]=prev;renderAll();var m=box.querySelector('.tmsg');if(m)m.textContent='Couldn\u2019t save \u2014 check your connection and try again.';});}
document.addEventListener('click',function(e){var b=e.target.closest('#tagBar .chip');if(b){window.rbTag=window.rbTag===b.dataset.t?'':b.dataset.t;renderAll();return;}
var box=e.target.closest('.rtags');if(!box)return;var rid=box.dataset.rid,t=tags(rid).slice();
if(e.target.closest('.chip.add')){box.classList.toggle('adding');renderEd(box);var i=box.querySelector('.tagnew input');return;}
var rm=e.target.closest('.chip.ed');if(rm){save(box,t.filter(function(x){return x!==rm.dataset.t}));return;}
var ad=e.target.closest('[data-add]');if(ad){box.classList.remove('adding');if(t.indexOf(ad.dataset.add)<0)t.push(ad.dataset.add);save(box,t);}});
document.addEventListener('submit',function(e){var f=e.target.closest('.tagnew');if(!f)return;e.preventDefault();var box=f.closest('.rtags'),v=canon(f.querySelector('input').value),t=tags(box.dataset.rid).slice();
if(!v)return;box.classList.remove('adding');if(t.map(norm).indexOf(norm(v))<0)t.push(v);save(box,t);});
function load(){return SB('recipe_tags?select=recipe_id,tags').then(function(rows){ok=true;var d={};(rows||[]).forEach(function(r){d[r.recipe_id]=(r.tags||[]).filter(Boolean)});cur=d;renderAll();})
.catch(function(er){if(/^40[04]/.test(er.message)||/recipe_tags/.test(er.message))ok=false;});}
renderAll();load();setInterval(function(){if(!document.hidden&&!document.querySelector('.rtags.adding'))load()},30000);
document.addEventListener('visibilitychange',function(){if(!document.hidden)load();});
})();
</script>""" % (json.dumps(KNOWN_TAGS), json.dumps({r["id"]: tags_of(r) for r in R if tags_of(r)}, ensure_ascii=False)))
CART_HTML = """<div class="toast" id="toast" role="status" aria-live="polite"></div>
<div class="cart-bg" id="cartBg"><div class="cart" role="dialog" aria-modal="true" aria-labelledby="cartTitle">
<div class="cart-h"><h3 id="cartTitle">Shopping Cart</h3><button type="button" id="cartClose" aria-label="Close cart">"""+ic("close")+"""</button></div>
<div class="cart-body">
<div class="shop"><label for="zipIn">Your zip code</label><div class="ziprow"><input id="zipIn" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="5" placeholder="12345" autocomplete="postal-code">
<button type="button" class="gobtn" id="goBtn">"""+ic("bag")+"""Let&rsquo;s go shopping</button></div><p class="shopmsg" id="shopMsg"></p></div>
<form class="cust" id="custForm"><input id="custIn" type="text" placeholder="Add an item (e.g. milk)" enterkeyhint="done" autocomplete="off"><button type="submit">Add</button></form>
<p class="cstat" id="cstat"></p><div id="cartList"></div>
<div class="shopstat" id="shopStatus" hidden><span class="cartspin" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 3.5h2.2l2 10.5h11.2l1.8-7.5H5.6"/><path d="M6.7 14l-.5 2.2h12"/><g class="wheel"><circle cx="9" cy="19.6" r="1.9"/><path d="M9 17.7v3.8M7.1 19.6h3.8"/></g><g class="wheel"><circle cx="16.8" cy="19.6" r="1.9"/><path d="M16.8 17.7v3.8M14.9 19.6h3.8"/></g></svg></span><div><b>Sous-Chef is out shopping&hellip;</b><small id="shopStatusTxt">Comparing clean picks and prices at nearby stores. Results will show up here.</small><div class="sprog" id="shopProg" hidden><div id="shopProgBar"></div></div></div></div><div class="shop res" id="results" hidden></div></div>
<div class="cart-f"><button type="button" id="clrChecked">Clear checked</button><button type="button" id="clrAll">Clear all</button></div></div></div>
<script>
(function(){
var HIDE=""" + HIDE_RE + """,REC=""" + json.dumps({r["id"]: {"t": r["title"], "i": r["ingredients"]} for r in R}, ensure_ascii=False) + """;
var items=[],$=function(i){return document.getElementById(i)},IC=""" + json.dumps({k: ic(k) for k in ("leaf","tag","pencil","trash","close")}) + """;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function safeUrl(u){return /^https?:\\/\\//i.test(u||'')?u:null;}
function toast(t){var el=$('toast');el.textContent=t;el.classList.add('show');clearTimeout(el._t);el._t=setTimeout(function(){el.classList.remove('show')},2200);}
var seq=0;function load(){var my=++seq;return SB('cart_items?select=*&order=sort_order.asc,created_at.asc').then(function(x){if(my===seq){items=x;render();}}).catch(function(){});}
function act(p,okMsg){$('cstat').textContent='Saving\\u2026';return p.then(function(r){return load().then(function(){$('cstat').textContent='';if(okMsg)toast(okMsg);return r});})
.catch(function(){$('cstat').textContent='Couldn\\u2019t save \\u2014 check your connection and try again.';toast('Couldn\\u2019t save \\u2014 try again');load();});}
var CGK='rb.cartCollapsed';function cgGet(){try{return JSON.parse(localStorage.getItem(CGK)||'{}')||{}}catch(x){return {}}}
function cgSet(o){try{localStorage.setItem(CGK,JSON.stringify(o))}catch(x){}}
function render(){var n=items.filter(function(i){return !i.checked}).length,c=$('cartCnt');c.textContent=n>99?'99+':n;c.hidden=!n;
var L=$('cartList');if(!items.length){L.innerHTML='<p class="empty">Your cart is empty. Add a recipe\\u2019s ingredients from its page, or add an item above.</p>';return;}
var groups={},order=[];items.forEach(function(i){var k=i.recipe_id||'';if(!groups[k]){groups[k]=[];order.push(k)}groups[k].push(i);});
order.sort(function(a,b){return (a===''?1:0)-(b===''?1:0)});
var CG=cgGet(),allC=order.every(function(k){return CG[k||'_other']});
L.innerHTML=(order.length>1?'<div class="grp-all"><button type="button" id="grpAll" data-all="'+(allC?'0':'1')+'">'+(allC?'Expand all':'Collapse all')+'</button></div>':'')+order.map(function(k){var g=groups[k],title=k?(g[0].recipe_title||(REC[k]&&REC[k].t)||k):'Other items',ck=k||'_other',col=!!CG[ck],left=g.filter(function(i){return !i.checked}).length,cnt=left===g.length?g.length+(g.length===1?' item':' items'):left+' of '+g.length+' left';
return '<div class="grp'+(col?' collapsed':'')+'" data-gk="'+esc(ck)+'"><div class="grp-h"><button type="button" class="grp-t" aria-expanded="'+(!col)+'"><span class="chev" aria-hidden="true"></span><span class="grp-nm">'+esc(title)+'</span><small class="grp-n">'+cnt+'</small></button><button type="button" class="grp-rm" data-delgrp="'+esc(k)+'">Remove</button></div>'+g.map(function(i){
return '<div class="it'+(i.checked?' done':'')+'" data-id="'+esc(i.id)+'"><input type="checkbox" aria-label="Check off '+esc(i.text)+'"'+(i.checked?' checked':'')+'><span class="t">'+esc(i.text)+'</span><button type="button" class="edit" aria-label="Edit">'+IC.pencil+'</button><button type="button" class="del" aria-label="Delete">'+IC.trash+'</button></div>';}).join('')+'</div>';}).join('');}
function money(v){return (typeof v==='number')?'$'+v.toFixed(2):esc(v||'');}
function num(v){return typeof v==='number'?v:null;}
var FL={palm_or_seed_oil:'Seed/palm oil',added_sugar:'Added sugar',dough_conditioner_emulsifier:'Dough conditioner/emulsifier',gum_stabilizer:'Gum/stabilizer',artificial_additive_preservative:'Additive/preservative',minor_aid:'Minor additive',non_organic:'Not organic',ultra_processed:'Ultra-processed'};
function ring(s){if(num(s)==null)return '';var c=s>=85?'g':s>=65?'a':'r',d=Math.max(0,Math.min(100,s));return '<span class="ring '+c+'" title="Clean score '+d+'/100" aria-label="Clean score '+d+' out of 100" style="--p:'+d+'"><b>'+Math.round(d)+'</b></span>';}
function pickLine(p){var u=safeUrl(p.url),c=p.coupon,fp=num(p.final_price)!=null?p.final_price:(num(p.price)!=null&&c&&num(c.savings)!=null?p.price-c.savings:null);
var h='<div class="pick">'+(num(p.clean_score)!=null?'<span class="cs '+(p.clean_score>=85?'g':p.clean_score>=65?'a':'r')+'">'+p.clean_score+'</span>':'')+'<span class="pp">'+money(p.price)+(p.unit?' <small>/ '+esc(p.unit)+'</small>':'')+'</span><div class="pn">'+esc(p.item)+': '+(u?'<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(p.product)+'</a>':esc(p.product))+(p.brand?' <small>('+esc(p.brand)+')</small>':'')+'</div>'+(p.why_clean?'<div class="pw">'+IC.leaf+'<span>'+esc(p.why_clean)+'</span></div>':'');
if(c){var cu=safeUrl(c.source_url);h+='<div class="cp"><span>'+IC.tag+' '+esc(c.description||'Coupon')+(c.type?' <small>('+esc(String(c.type).replace('_',' '))+')</small>':'')+(cu?' <a href="'+esc(cu)+'" target="_blank" rel="noopener">details</a>':'')+'</span><span>'+(num(c.savings)!=null?'&minus;'+money(c.savings):'')+'</span></div>';}
var fl=Array.isArray(p.ingredient_flags)?p.ingredient_flags:[];if(fl.length)h+='<div class="fl">'+fl.map(function(f){return '<span>'+esc(FL[f]||f)+'</span>'}).join('')+'</div>';
if(p.ingredients_checked===false)h+='<div class="fl"><span class="uv">Label not verified</span></div>';
if(p.swap)h+='<div class="swp">'+IC.leaf+'<span>'+esc(p.swap)+'</span></div>';
if(c&&fp!=null)h+='<div class="fp">Final <span>'+money(fp)+'</span></div>';return h+'</div>';}
function sums(s){return '<div class="sum"><div>Subtotal <span>'+money(num(s.subtotal)!=null?s.subtotal:s.total)+'</span></div>'+(num(s.coupon_savings)?'<div class="cp">Coupons saved <span>&minus;'+money(s.coupon_savings)+'</span></div>':'')+'<div class="tot">Total <span>'+money(s.total)+'</span></div></div>';}
function custPair(){try{var v=JSON.parse(localStorage.getItem('custPair')||'[]');return Array.isArray(v)?v.slice(0,2):[]}catch(e){return []}}
function setPair(p){try{localStorage.setItem('custPair',JSON.stringify(p))}catch(e){};_ro.cust=true;renderResults(window._rows);}
function custSplit(r,a,b){var picks=(r.picks||[]).filter(function(p){return !p.pantry&&!p.optional&&num(p.final_price)!=null}),lines=[],asg=[],miss=[];
picks.forEach(function(p){if(lines.indexOf(p.item)<0)lines.push(p.item)});
lines.forEach(function(l){var c=picks.filter(function(p){return p.item===l&&(p.store===a||p.store===b)});if(!c.length){miss.push(l);return;}
var top=Math.max.apply(null,c.map(function(p){return num(p.clean_score)||0}));var t=c.filter(function(p){return (num(p.clean_score)||0)>=top-3}).sort(function(x,y){return x.final_price-y.final_price});asg.push(t[0]);});
var tot=asg.reduce(function(s,p){return s+p.final_price},0),cs=asg.reduce(function(s,p){return s+((p.coupon&&num(p.coupon.savings))||0)},0);
var sc=asg.length?Math.round(10*asg.reduce(function(s,p){return s+(num(p.clean_score)||0)},0)/asg.length)/10:null;
return {asg:asg,miss:miss,total:Math.round(tot*100)/100,coupons:Math.round(cs*100)/100,score:sc};}
function custBox(r,byId){var st=(r.stores||[]);if(st.length<2||!(r.picks||[]).length)return '';var pr=custPair().filter(function(id){return byId[id]});
var nm=function(id){return byId[id]?byId[id].name:id},sn=function(id){return nm(id).replace(HIDE,'').trim()};
var h='<details data-k="cust" class="store csplit"'+(rOpen('cust',false)?' open':'')+'><summary><div class="sh"><span>Custom 2-store split</span><span class="tr" id="custTr">';
var res=pr.length===2?custSplit(r,pr[0],pr[1]):null;
if(res)h+=ring(res.score)+money(res.total);h+='</span></div><div class="sa">'+(res?esc(nm(pr[0])+' + '+nm(pr[1])):'Drag or tap any two stores')+'</div></summary>';
h+='<div class="chips2" id="custChips">'+st.map(function(s){var on=pr.indexOf(s.id)>=0;return '<button type="button" class="schip'+(on?' on':'')+'" draggable="true" data-sid="'+esc(s.id)+'"'+(on?' aria-pressed="true"':'')+'>'+ring(s.clean_score)+'<span>'+esc(sn(s.id))+'</span></button>'}).join('')+'</div>';
h+='<div class="bubble" id="custBubble">'+[0,1].map(function(i){var id=pr[i];return '<button type="button" class="slot'+(id?' full':'')+'" data-slot="'+i+'" aria-label="'+(id?'Remove '+esc(nm(id)):'Empty slot '+(i+1))+'">'+(id?'<em>'+esc(sn(id))+'</em><i aria-hidden="true">'+IC.close+'</i>':'<span>Drop a store</span>')+'</button>'}).join('<span class="plus" aria-hidden="true">+</span>')+'</div>';
if(res){var cl=st.filter(function(s){return num(s.clean_score)!=null&&num(s.total)!=null}).sort(function(x,y){return y.clean_score-x.clean_score||x.total-y.total})[0];
var sv=cl?Math.round((cl.total-res.total)*100)/100:null;
h+='<div class="custres" id="custRes">'+ring(res.score)+'<div><b>'+money(res.total)+'</b><small>Clean score '+res.score+(res.coupons?' &middot; '+money(res.coupons)+' in sales':'')+'</small>'+(cl&&sv!=null?'<small class="sv">'+(sv>=0?'Saves '+money(sv):money(-sv)+' more')+' vs. '+esc(cl.name)+' alone (cleanest, score '+cl.clean_score+')</small>':'')+'</div></div>';
if(res.miss.length)h+='<div class="miss">Neither store has: '+res.miss.map(esc).join(', ')+'</div>';
h+='<details data-k="custlist" class="wbw"'+(rOpen('custlist',false)?' open':'')+'><summary>What to buy where</summary>'+pr.map(function(id){var its=res.asg.filter(function(p){return p.store===id});return '<div class="hgrp"><b>'+esc(nm(id))+' <small>'+its.length+' items &middot; '+money(its.reduce(function(s,p){return s+p.final_price},0))+'</small></b><ul>'+its.map(function(p){return '<li><span class="cs '+(p.clean_score>=85?'g':p.clean_score>=65?'a':'r')+'">'+p.clean_score+'</span> '+esc(String(p.item).split(' \u2014 ')[0])+' <small>'+esc(p.product)+' &middot; '+money(p.final_price)+'</small></li>'}).join('')+'</ul></div>'}).join('')+'</details>'+cartBtn('cust:'+pr.join('+'),pr.map(function(id){return {store:id,name:nm(id),items:cartItems(res.asg.filter(function(p){return p.store===id}))}}));}
return h+'</details>';}
(function(){function fill(id){var p=custPair();if(p.indexOf(id)>=0)return;if(p.length<2)p.push(id);else p[1]=id;setPair(p);}
function put(id,i){var p=custPair();var j=p.indexOf(id);if(j>=0)p.splice(j,1);if(i>p.length)i=p.length;p[i]=id;setPair(p.filter(Boolean).slice(0,2));}
var suppress=0;
document.addEventListener('click',function(e){var c=e.target.closest&&e.target.closest('.schip');if(c){if(Date.now()<suppress)return;fill(c.dataset.sid);return;}
var s=e.target.closest&&e.target.closest('.slot.full');if(s){var p=custPair();p.splice(+s.dataset.slot,1);setPair(p);}});
document.addEventListener('dragstart',function(e){var c=e.target.closest&&e.target.closest('.schip');if(!c)return;e.dataTransfer.setData('text/plain',c.dataset.sid);e.dataTransfer.effectAllowed='copy';c.classList.add('drag');});
document.addEventListener('dragend',function(e){var c=e.target.closest&&e.target.closest('.schip');if(c)c.classList.remove('drag');document.querySelectorAll('.slot.over').forEach(function(x){x.classList.remove('over')});});
document.addEventListener('dragover',function(e){var s=e.target.closest&&e.target.closest('.slot');if(!s)return;e.preventDefault();s.classList.add('over');});
document.addEventListener('dragleave',function(e){var s=e.target.closest&&e.target.closest('.slot');if(s)s.classList.remove('over');});
document.addEventListener('drop',function(e){var s=e.target.closest&&e.target.closest('.slot');if(!s)return;e.preventDefault();var id=e.dataTransfer.getData('text/plain');if(id)put(id,+s.dataset.slot);});
var drag=null;
document.addEventListener('pointerdown',function(e){if(e.pointerType==='mouse')return;var c=e.target.closest&&e.target.closest('.schip');if(!c)return;drag={c:c,x:e.clientX,y:e.clientY,g:null,id:e.pointerId};},{passive:true});
document.addEventListener('pointermove',function(e){if(!drag||e.pointerId!==drag.id)return;var dx=e.clientX-drag.x,dy=e.clientY-drag.y;
if(!drag.g){if(Math.abs(dx)+Math.abs(dy)<8)return;var g=drag.c.cloneNode(true);g.className='schip ghost';var b=drag.c.getBoundingClientRect();g.style.width=b.width+'px';drag.ox=drag.x-b.left;drag.oy=drag.y-b.top;document.body.appendChild(g);drag.g=g;drag.c.classList.add('drag');}
drag.g.style.transform='translate('+(e.clientX-drag.ox)+'px,'+(e.clientY-drag.oy)+'px) scale(1.06)';
var el=document.elementFromPoint(e.clientX,e.clientY),s=el&&el.closest('.slot');document.querySelectorAll('.slot.over').forEach(function(x){if(x!==s)x.classList.remove('over')});if(s)s.classList.add('over');});
function end(e){if(!drag||e.pointerId!==drag.id)return;var d=drag;drag=null;if(!d.g)return;suppress=Date.now()+400;d.g.remove();d.c.classList.remove('drag');
var el=e.type==='pointerup'&&document.elementFromPoint(e.clientX,e.clientY),s=el&&el.closest('.slot');document.querySelectorAll('.slot.over').forEach(function(x){x.classList.remove('over')});if(s)put(d.c.dataset.sid,+s.dataset.slot);}
document.addEventListener('pointerup',end);document.addEventListener('pointercancel',end);})();

var CARTURL={heb:'https://www.heb.com/cart',walmart:'https://www.walmart.com/cart',sprouts:'https://shop.sprouts.com/store/sprouts/storefront?open_cart=true',target:'https://www.target.com/cart',amazon:'https://www.amazon.com/cart',wholefoods:'https://www.amazon.com/cart'},MYCARTS=""" + json.dumps(STORE_CARTS) + """;
function cartUrl(id,name){var mine=MYCARTS[String(id).toLowerCase()];if(/^https?:\\/\\//i.test(mine||''))return mine;var k=(String(id)+' '+(name||'')).toLowerCase();if(/h-?e-?b|central market/.test(k))return CARTURL.heb;if(/walmart/.test(k))return CARTURL.walmart;if(/sprouts/.test(k))return CARTURL.sprouts;if(/target/.test(k))return CARTURL.target;if(/amazon|whole ?foods/.test(k))return CARTURL.amazon;return null;}
function shortName(n){return String(n||'').replace(HIDE,'').trim();}
window._cpay={};window._creq=[];
function cartItems(ps){return ps.filter(function(p){return p&&!p.pantry&&p.product}).map(function(p){return {name:String(p.item||'').split(' \u2014 ')[0],product:p.product,url:safeUrl(p.url),qty:num(p.qty)||1,unit:p.unit||null,price:num(p.final_price)!=null?p.final_price:num(p.price)}});}
function cartBtn(key,groups){groups=groups.filter(function(g){return g.items.length});if(!groups.length)return '';window._cpay[key]=groups;
return '<div class="send" data-ckey="'+esc(key)+'"><button type="button" class="sendbtn" data-send="'+esc(key)+'">Send to cart</button><div class="cst"></div></div>';}
var CSTX={queued:'Queued',working:'Adding\u2026',done:'Added',partial:'Partly added',failed:'Couldn\u2019t add'};
function paintCarts(){document.querySelectorAll('.send[data-ckey]').forEach(function(el){var k=el.dataset.ckey,rid=window._rows&&window._rows[0]&&window._rows[0].id;
var rs=window._creq.filter(function(c){return c.source===k&&c.result_id===rid});var latest={};rs.forEach(function(c){if(!latest[c.store]||c.id>latest[c.store].id)latest[c.store]=c});var L=Object.keys(latest).map(function(s){return latest[s]});
var busy=L.some(function(c){return c.status==='queued'||c.status==='working'}),b=el.querySelector('.sendbtn');b.disabled=busy;b.textContent=busy?'Sending\u2026':L.length?'Send again':'Send to cart';
el.querySelector('.cst').innerHTML=L.map(function(c){var u=cartUrl(c.store,c.store_name),n=(c.added||[]).length,f=(c.failed||[]).length,t=CSTX[c.status]||c.status;
if(c.status==='done'||c.status==='partial')t+=' '+n+' of '+(c.items||[]).length;
return '<div class="cs1 '+esc(c.status)+'"><i></i><span><b>'+esc(shortName(c.store_name||c.store))+'</b> '+esc(t)+(f&&c.status!=='done'?' &middot; '+f+' not found':'')+(c.note?' <small>'+esc(c.note)+'</small>':'')+'</span>'+((c.status==='done'||c.status==='partial')&&u?'<a href="'+u+'" target="_blank" rel="noopener">Open '+esc(shortName(c.store_name||c.store))+' cart</a>':'')+'</div>'}).join('');});}
var _cpoll=null;function loadCarts(){var row=window._rows&&window._rows[0];if(!row)return Promise.resolve();
return SB('cart_requests?result_id=eq.'+encodeURIComponent(row.id)+'&select=*&order=id.asc').then(function(x){window._creq=x||[];paintCarts();var busy=_creq.some(function(c){return c.status==='queued'||c.status==='working'});
clearTimeout(_cpoll);if(busy)_cpoll=setTimeout(function(){if(!document.hidden)loadCarts();else _cpoll=setTimeout(loadCarts,8000)},6000);}).catch(function(){});}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-send]');if(!b)return;e.preventDefault();var k=b.dataset.send,g=window._cpay[k],row=window._rows&&window._rows[0];if(!g||!row)return;
if(!confirm('Add '+g.map(function(x){return x.items.length+' items to '+shortName(x.name)}).join(' and ')+'? Nothing is ordered \u2014 you check out yourselves.'))return;b.disabled=true;b.textContent='Sending\u2026';
SB('cart_requests',{method:'POST',prefer:'return=minimal',body:g.map(function(x){return {shopping_request_id:row.request_id||null,result_id:row.id,source:k,store:x.store,store_name:x.name,items:x.items}})})
.then(function(){toast('Sent \u2014 items will appear in the cart soon');return loadCarts();}).catch(function(){b.disabled=false;b.textContent='Send to cart';alert("Couldn't send. Check your connection and try again.")});});
function renderResults(rows){var box=$('results');window._rows=rows;if(!rows||!rows.length){box.hidden=true;return;}var row=rows[0],r=row.result||{},st=r.stores||[],picks=r.picks||[];
var byId={};st.forEach(function(s){byId[s.id]=s});
var priced=st.filter(function(s){return num(s.total)!=null}).sort(function(a,b){return a.total-b.total});
var top=(Array.isArray(r.top3)&&r.top3.length?r.top3.map(function(id){return byId[id]}).filter(Boolean):priced).slice(0,3);
var full=priced.filter(function(s){return !(Array.isArray(s.items_missing)&&s.items_missing.length)});var cheapest=(r.cheapest_store&&byId[r.cheapest_store])||full[0]||priced[0]||null;
var h='<h4>Shopping results<button type="button" class="delres" data-delres="'+esc(String(row.id))+'" aria-label="Delete these results">Delete</button></h4><div class="when">'+esc(new Date(row.created_at).toLocaleString())+(r.zip||row.zip?' &middot; zip '+esc(r.zip||row.zip):'')+'</div>';
if(!window.rOpen){window._ro={};window.rOpen=function(k,d){return k in _ro?_ro[k]:d};document.addEventListener('toggle',function(e){var t=e.target;if(t.dataset&&t.dataset.k)_ro[t.dataset.k]=t.open},true);}
if(top.length){h+='<h5 class="rh">Top '+top.length+' store'+(top.length>1?'s':'')+'</h5>';
h+=top.map(function(s,ix){var ps=picks.filter(function(p){return p.store===s.id||p.store===s.name});
var miss=Array.isArray(s.items_missing)?s.items_missing:[];
return '<details data-k="'+esc(s.id)+'" class="store'+(s===cheapest?' cheap':'')+'"'+(rOpen(s.id,ix===0)?' open':'')+'><summary><div class="sh"><span>'+(ix+1)+'. '+esc(s.name)+'</span><span class="tr">'+ring(s.clean_score)+money(s.total)+'</span></div><div class="sa">'+esc(s.address||'')+(s.distance_mi!=null?' &middot; '+esc(s.distance_mi)+' mi':'')+(s.items_found!=null?' &middot; '+esc(s.items_found)+' found':'')+(miss.length?' &middot; '+miss.length+' missing':'')+(num(s.coupon_savings)?' &middot; <b class="sv">'+money(s.coupon_savings)+' coupons</b>':'')+'</div></summary>'+
ps.map(pickLine).join('')+(miss.length?'<div class="miss">Not found here: '+miss.map(esc).join(', ')+'</div>':'')+(ps.length||num(s.total)!=null?sums(s):'')+cartBtn('store:'+s.id,[{store:s.id,name:s.name,items:cartItems(ps)}])+'</details>';}).join('');}
var hsplit=h.length;
var hy=r.hybrid;
if(hy&&Array.isArray(hy.assignments)&&hy.assignments.length){var hs=(hy.stores||[]).map(function(id){return byId[id]?byId[id].name:id});
h+='<details data-k="hyb" class="store hyb"'+(rOpen('hyb',false)?' open':'')+'><summary><div class="sh"><span>Best 2-store split</span><span class="tr">'+ring(hy.clean_score)+money(hy.total)+'</span></div><div class="sa">'+esc(hs.join(' + '))+(num(hy.savings_vs_best_single)?' &middot; <b class="sv">saves '+money(hy.savings_vs_best_single)+'</b> '+esc(hy.savings_label||'vs. one store'):'')+'</div></summary>';
(hy.stores||[]).forEach(function(id){var its=hy.assignments.filter(function(a){return a.store===id});if(!its.length)return;h+='<div class="hgrp"><b>'+esc(byId[id]?byId[id].name:id)+'</b><ul>'+its.map(function(a){return '<li>'+esc(a.item)+'</li>'}).join('')+'</ul></div>';});
h+=sums(hy)+cartBtn('hyb',(hy.stores||[]).map(function(id){return {store:id,name:byId[id]?byId[id].name:id,items:cartItems(hy.assignments.filter(function(a){return a.store===id}).map(function(a){return picks.filter(function(p){return p.store===id&&p.item===a.item})[0]||null}))}}))+(hy.note?'<p class="notes">'+esc(hy.note)+'</p>':'')+'</details>';}
h+=custBox(r,byId);
if(h.length>hsplit)h=h.slice(0,hsplit)+'<h5 class="rh">2-store splits</h5>'+h.slice(hsplit);
var rest=st.filter(function(s){return top.indexOf(s)<0});
if(st.length){h+='<h5 class="rh">All stores checked</h5><ul class="all">'+st.map(function(s){return '<li><span>'+esc(s.name)+(s.distance_mi!=null?' <small>'+esc(s.distance_mi)+' mi</small>':'')+'</span><span class="tr">'+ring(s.clean_score)+(num(s.total)!=null?money(s.total):'<small>no prices</small>')+'</span></li>'}).join('')+'</ul>';}
if(r.notes)h+='<p class="notes">'+esc(r.notes)+'</p>';box.innerHTML=h;box.hidden=false;paintCarts();loadCarts();}
document.addEventListener('click',function(e){var d=e.target.closest&&e.target.closest('[data-delres]');if(!d)return;if(!confirm('Delete these shopping results?'))return;d.disabled=true;SB('shopping_results?id=eq.'+encodeURIComponent(d.dataset.delres),{method:'DELETE'}).then(loadResults).catch(function(){d.disabled=false;alert("Couldn't delete. Check your connection and try again.")});});
function loadStatus(){return SB('shopping_requests?status=in.(pending,processing)&select=id,status,created_at,stores_done,stores_total,current_store&order=id.desc&limit=1').then(function(r){var on=r&&r.length;$('shopStatus').hidden=!on;$('cartBtn').classList.toggle('shopping',!!on);if(on){var m=Math.max(0,Math.round((Date.now()-new Date(r[0].created_at))/60000));var q=r[0],pr=q.stores_total?(q.stores_done||0)+' of '+q.stores_total+' stores shopped'+(q.current_store?' \u00b7 now at '+q.current_store:'')+'. ':'';$('shopStatusTxt').textContent=(q.status==='pending'?'Request received, heading out soon. ':pr||'Comparing clean picks and prices at nearby stores. ')+'Started '+(m<1?'just now':m+' min ago')+'.';$('shopProg').hidden=!q.stores_total;if(q.stores_total)$('shopProgBar').style.width=Math.round(100*(q.stores_done||0)/q.stores_total)+'%';}}).catch(function(){});}
function loadResults(){loadStatus();return SB('shopping_results?select=*&order=created_at.desc&limit=1').then(renderResults).catch(function(){});}
var HOMEZIP=""" + json.dumps(str(CFG.get("home_zip") or "")) + """;
function loadZip(){if(HOMEZIP&&!$('zipIn').value)$('zipIn').value=HOMEZIP;return SB('settings?key=eq.zip&select=value').then(function(r){if(r[0]&&r[0].value&&document.activeElement!==$('zipIn'))$('zipIn').value=r[0].value;}).catch(function(){});}
function openCart(){$('cartBg').classList.add('open');document.body.style.overflow='hidden';load();loadZip();loadResults();}
function closeCart(){$('cartBg').classList.remove('open');document.body.style.overflow='';}
$('cartBtn').addEventListener('click',openCart);$('cartClose').addEventListener('click',closeCart);
$('cartBg').addEventListener('click',function(e){if(e.target===$('cartBg'))closeCart();});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&$('cartBg').classList.contains('open'))closeCart();});
document.addEventListener('click',function(e){var b=e.target.closest('.cartadd');if(!b)return;var rid=b.dataset.rid,R_=REC[rid];if(!R_)return;b.disabled=true;
SB('cart_items?select=id&limit=1&recipe_id=eq.'+encodeURIComponent(rid)).then(function(ex){
if(ex.length&&!confirm('\\u201c'+R_.t+'\\u201d is already in the cart. Add its ingredients again?\\n\\nOK = add again, Cancel = skip')){toast('Skipped \\u2014 already in cart');return;}
var base=Date.now()/1000;return act(SB('cart_items',{method:'POST',prefer:'return=minimal',body:R_.i.map(function(t,ix){return {recipe_id:rid,recipe_title:R_.t,text:t,sort_order:base+ix/1000}})}),'Added '+R_.i.length+' items \\u2713');})
.catch(function(){toast('Couldn\\u2019t reach the cart \\u2014 try again');}).then(function(){b.disabled=false;});});
$('custForm').addEventListener('submit',function(e){e.preventDefault();var t=$('custIn').value.trim();if(!t)return;$('custIn').value='';
act(SB('cart_items',{method:'POST',prefer:'return=minimal',body:{text:t}}),'Added \\u2713');});
function upd(id,patch){return SB('cart_items?id=eq.'+id,{method:'PATCH',prefer:'return=minimal',body:patch});}
$('cartList').addEventListener('change',function(e){if(e.target.type!=='checkbox')return;var id=e.target.closest('.it').dataset.id,v=e.target.checked;
e.target.closest('.it').classList.toggle('done',v);act(upd(id,{checked:v}));});
$('cartList').addEventListener('click',function(e){var row=e.target.closest('.it'),g=e.target.closest('[data-delgrp]');
var tg=e.target.closest('.grp-t');if(tg){var gp=tg.closest('.grp'),gk=gp.dataset.gk,o=cgGet(),c=!gp.classList.contains('collapsed');if(c)o[gk]=1;else delete o[gk];cgSet(o);gp.classList.toggle('collapsed',c);tg.setAttribute('aria-expanded',!c);var ab=$('grpAll');if(ab){var ac=[].every.call(document.querySelectorAll('#cartList .grp'),function(x){return x.classList.contains('collapsed')});ab.dataset.all=ac?'0':'1';ab.textContent=ac?'Expand all':'Collapse all';}return;}
var ga=e.target.closest('#grpAll');if(ga){var on=ga.dataset.all==='1',o2=cgGet();[].forEach.call(document.querySelectorAll('#cartList .grp'),function(x){if(on)o2[x.dataset.gk]=1;else delete o2[x.dataset.gk];});cgSet(o2);render();return;}
if(g){var k=g.dataset.delgrp;if(confirm('Remove all items for this recipe?'))act(SB('cart_items?'+(k?'recipe_id=eq.'+encodeURIComponent(k):'recipe_id=is.null'),{method:'DELETE'}),'Removed \\u2713');return;}
if(!row)return;var id=row.dataset.id;
if(e.target.closest('.del')){row.style.opacity=.4;act(SB('cart_items?id=eq.'+id,{method:'DELETE'}));return;}
if(e.target.closest('.edit')){var sp=row.querySelector('.t'),old=sp.textContent,inp=document.createElement('input');inp.className='ed';inp.value=old;sp.replaceWith(inp);inp.focus();var done=false;
function fin(save){if(done)return;done=true;var v=inp.value.trim();if(save&&v&&v!==old)act(upd(id,{text:v}));else render();}
inp.addEventListener('keydown',function(k){if(k.key==='Enter'){k.preventDefault();fin(true)}if(k.key==='Escape')fin(false)});inp.addEventListener('blur',function(){fin(true)});}});
$('clrChecked').addEventListener('click',function(){if(!items.some(function(i){return i.checked})){toast('Nothing checked yet');return;}act(SB('cart_items?checked=is.true',{method:'DELETE'}),'Cleared checked items \\u2713');});
$('clrAll').addEventListener('click',function(){if(!items.length)return;if(confirm('Clear the whole shopping cart for everyone?'))act(SB('cart_items?id=not.is.null',{method:'DELETE'}),'Cart cleared');});
$('zipIn').addEventListener('input',function(){this.value=this.value.replace(/\\D/g,'').slice(0,5);var z=this.value;if(z.length===5)SB('settings?on_conflict=key',{method:'POST',prefer:'resolution=merge-duplicates,return=minimal',body:{key:'zip',value:z}}).then(function(){toast('Zip saved \\u2713')}).catch(function(){});});
$('goBtn').addEventListener('click',function(){var z=$('zipIn').value,m=$('shopMsg'),btn=this;m.className='shopmsg';
if(!/^[0-9]{5}$/.test(z)){m.className='shopmsg err';m.textContent='Enter your 5-digit zip code first.';$('zipIn').focus();return;}
var un=items.filter(function(i){return !i.checked});if(!un.length){m.className='shopmsg err';m.textContent='Your cart has no unchecked items to shop for.';return;}
var who='';try{who=localStorage.getItem('rb-addedBy')||''}catch(_){}
btn.disabled=true;m.textContent='Sending\\u2026';
SB('settings?on_conflict=key',{method:'POST',prefer:'resolution=merge-duplicates,return=minimal',body:{key:'zip',value:z}}).catch(function(){}).then(function(){
return SB('shopping_requests',{method:'POST',prefer:'return=minimal',body:{zip:z,requested_by:who||null,items:un.map(function(i){return {text:i.text,recipe_id:i.recipe_id,recipe_title:i.recipe_title}})}});})
.then(function(){m.className='shopmsg ok';m.textContent='Sous-Chef is on it! Results will show up here.';})
.catch(function(){m.className='shopmsg err';m.textContent='Couldn\\u2019t send \\u2014 check your connection and try again.';}).then(function(){btn.disabled=false;});});
load();document.addEventListener('visibilitychange',function(){if(!document.hidden){load();if($('cartBg').classList.contains('open')){loadResults();loadZip();}}});
setInterval(function(){if(!document.hidden&&$('cartBg').classList.contains('open')){load();loadResults();}},20000);loadStatus();setInterval(function(){if(!document.hidden)loadStatus();},30000);
})();
</script>"""

ADD_HTML = """<button class="fab" id="addBtn" type="button" aria-haspopup="dialog">"""+ic("plus")+"""Add Recipe</button>
<div class="sheet-bg" id="sheetBg"><div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetTitle">
<button class="x" id="closeSheet" type="button" aria-label="Close">"""+ic("close")+"""</button><h3 id="sheetTitle">Add a recipe</h3>
<form id="addForm" novalidate><div class="sbody"><label for="recLink">Recipe link</label><div class="row">
<input id="recLink" type="url" autofocus inputmode="url" autocomplete="off" autocapitalize="off" placeholder="https://..." required>
<button class="btn alt" id="pasteBtn" type="button">Paste</button></div><p class="err" id="err"></p>
<button type="button" class="addnote" id="addNote">+ Add note</button><div class="notewrap" id="noteWrap" hidden><label for="recNotes">Note</label><textarea id="recNotes" rows="1" placeholder="Anything to remember?"></textarea></div>
<label>Added by</label><div class="who-pick" id="whoPick">""" + "".join(f'<button type="button" data-w="{e(l)}">{e(l)}</button>' for _, l in RATERS) + """</div>
<button type="button" class="tagrow" id="tagRow" aria-expanded="false" aria-controls="tagPanel"><span class="tl">Tags</span><span class="tv" id="tagVal">None</span><span class="chev" aria-hidden="true"></span></button>
<div class="tagpanel" id="tagPanel"><div class="tpin"><div class="tagpick" id="tagPick"></div>
<button type="button" class="tmore" id="tagMore">More</button><div class="tagpick" id="tagPick2" hidden></div>
<div class="row tagcust"><input id="tagCust" type="text" placeholder="Custom tag" autocomplete="off" enterkeyhint="done" maxlength="40"><button class="btn alt" id="tagCustAdd" type="button">Add</button></div>
<button type="button" class="tdone" id="tagDone">Done</button></div></div>
<p class="ok" id="okMsg" hidden></p></div><div class="sfoot"><button class="btn go" id="sendBtn" type="submit">Send</button></div></form></div></div>
<script>
(function(){
var bg=document.getElementById('sheetBg'),link=document.getElementById('recLink'),
notes=document.getElementById('recNotes'),err=document.getElementById('err'),paste=document.getElementById('pasteBtn'),
ok=document.getElementById('okMsg'),send=document.getElementById('sendBtn'),pick=document.getElementById('whoPick'),busy=false;
var who='';try{who=localStorage.getItem('rb-addedBy')||''}catch(_){}
var KT=""" + json.dumps(KNOWN_TAGS) + """,sel=[],tp=document.getElementById('tagPick'),tc=document.getElementById('tagCust');
function tesc(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML;}
var tp2=document.getElementById('tagPick2'),tmore=document.getElementById('tagMore'),trow=document.getElementById('tagRow'),tpan=document.getElementById('tagPanel'),tval=document.getElementById('tagVal');
var cnt={};try{document.querySelectorAll('.card .tags').forEach(function(el){el.textContent;});}catch(_){}
document.querySelectorAll('.card[data-t]').forEach(function(c){(c.dataset.t||'').split('|').forEach(function(x){if(x)cnt[x]=(cnt[x]||0)+1})});
function nk(t){return t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'')}
var TOP=KT.slice().sort(function(a,b){return (cnt[nk(b)]||0)-(cnt[nk(a)]||0)}).slice(0,6);
function btn(t){return '<button type="button" class="'+(sel.indexOf(t)>=0?'on':'')+'" data-t="'+tesc(t)+'">'+tesc(t)+'</button>'}
function showTags(){var top=TOP.concat(sel.filter(function(t){return TOP.indexOf(t)<0&&KT.indexOf(t)<0}));tp.innerHTML=top.map(btn).join('');
tp2.innerHTML=KT.filter(function(t){return TOP.indexOf(t)<0}).map(btn).join('');
tval.innerHTML=sel.length?sel.map(function(t){return '<span class="mini">'+tesc(t)+'</span>'}).join(''):'None';}
function setT(o){tpan.classList.toggle('open',o);trow.setAttribute('aria-expanded',o);if(o)setTimeout(function(){trow.scrollIntoView({block:'start',behavior:'smooth'})},60);}
trow.addEventListener('click',function(){setT(!tpan.classList.contains('open'))});
document.getElementById('tagDone').addEventListener('click',function(){if(tc.value.trim())addCust();setT(false)});
tmore.addEventListener('click',function(){var h=!tp2.hidden;tp2.hidden=h;tmore.textContent=h?'More':'Fewer'});
tp2.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;var t=b.dataset.t,i=sel.indexOf(t);if(i>=0)sel.splice(i,1);else sel.push(t);showTags();});
var nw=document.getElementById('noteWrap'),an=document.getElementById('addNote');
an.addEventListener('click',function(){nw.hidden=false;an.hidden=true;notes.focus()});
function grow(){notes.style.height='auto';notes.style.height=Math.min(notes.scrollHeight,160)+'px'}notes.addEventListener('input',grow);
tp.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;var t=b.dataset.t,i=sel.indexOf(t);if(i>=0)sel.splice(i,1);else sel.push(t);showTags();});
function addCust(){var t=tc.value.trim().replace(/\\s+/g,' ');if(!t)return;var k=KT.filter(function(x){return x.toLowerCase()===t.toLowerCase()})[0]||t;if(sel.indexOf(k)<0)sel.push(k);tc.value='';showTags();}
document.getElementById('tagCustAdd').addEventListener('click',addCust);tc.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();addCust();}});showTags();
function showWho(){pick.querySelectorAll('button').forEach(function(b){b.classList.toggle('on',b.dataset.w===who)});}
pick.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;who=(who===b.dataset.w)?'':b.dataset.w;try{localStorage.setItem('rb-addedBy',who)}catch(_){}showWho();});showWho();
function open(){err.textContent='';setT(false);if(!notes.value){nw.hidden=true;an.hidden=false;}ok.hidden=true;send.textContent='Send';bg.classList.add('open');link.focus();}
function close(){bg.classList.remove('open');}
document.getElementById('addBtn').addEventListener('click',open);
document.getElementById('closeSheet').addEventListener('click',close);
bg.addEventListener('click',function(e){if(e.target===bg&&!busy)close();});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!busy)close();});
if(!(navigator.clipboard&&navigator.clipboard.readText))paste.style.display='none';
paste.addEventListener('click',function(){navigator.clipboard.readText().then(function(t){link.value=t.trim();err.textContent='';link.focus();})
.catch(function(){err.textContent='Clipboard not allowed here. Long-press the field and choose Paste.';link.focus();});});
document.getElementById('addForm').addEventListener('submit',function(e){e.preventDefault();if(busy)return;var u=link.value.trim();err.textContent='';
if(!u){err.textContent='Please paste a recipe link.';link.focus();return;}
if(!/^https?:\\/\\//i.test(u)){err.textContent='The link should start with http:// or https://';link.focus();return;}
if(tc.value.trim())addCust();var item={url:u,notes:notes.value.trim()};if(who)item.added_by=who;if(sel.length)item.tags=sel.slice();
busy=true;send.disabled=true;send.textContent='Adding\\u2026';
SB('recipe_queue',{method:'POST',prefer:'return=minimal',body:item}).catch(function(er){if(!item.tags)throw er;var b2={url:item.url,notes:(item.notes?item.notes+'\\n':'')+'Tags: '+item.tags.join(', ')};if(item.added_by)b2.added_by=item.added_by;return SB('recipe_queue',{method:'POST',prefer:'return=minimal',body:b2});}).then(function(){sel=[];showTags();ok.textContent='Added! \\u2713 It\\u2019ll appear in the book shortly';ok.hidden=false;send.textContent='Added \\u2713';
link.value='';notes.value='';setTimeout(function(){busy=false;send.disabled=false;close();},1800);})
.catch(function(){busy=false;send.disabled=false;send.textContent='Retry';err.textContent='Couldn\\u2019t save \\u2014 check your connection and tap Retry.';});});
})();
</script>"""
EMPTY = '' if R else '<div class="emptybook"><p><b>No recipes yet.</b></p><p>Tap <b>+ Add Recipe</b> and paste a link from any recipe site, Instagram, TikTok or YouTube. Your Grok Bot adds it to the book on its next check.</p></div>'
EYEBROW = f'<p class="eyebrow">{e(FAMILY)}</p>' if FAMILY else ''
open('index.html', 'w').write(f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#faf8f5" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0e0d0c" media="(prefers-color-scheme: dark)"><meta name="color-scheme" content="light dark"><link rel="manifest" href="manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{e(SHORT_NAME)}"><link rel="apple-touch-icon" href="icons/icon-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<title>{e(APP_NAME)}</title><style>{open("design.css").read()}</style></head><body><header class="bar glass"><a class="barback" href="#">{ic("back")}Recipes</a><span class="barspace"></span><div class="search" role="search"><span class="sicon" aria-hidden="true">{ic("search")}</span><input id="q" type="search" placeholder="Search recipes, ingredients, who added&hellip;" aria-label="Search recipes" autocomplete="off" autocorrect="off" spellcheck="false" enterkeyhint="search"><button type="button" id="qx" class="qx" aria-label="Clear search" hidden>{ic("close")}</button></div><button type="button" class="cartbtn" id="cartBtn" aria-label="Shopping cart">{ic("cart")}<span class="cnt" id="cartCnt" hidden>0</span></button></header>
<main><div class="intro">{EYEBROW}<h1>{e(APP_NAME)}</h1><p class="sub">{len(R)} recipes</p></div><div class="frow"><button type="button" class="chip rchip" id="rateChip" aria-haspopup="true" aria-controls="ratePick" aria-expanded="false">Rating</button><div class="tagbar" id="tagBar" hidden></div></div><div class="rpick" id="ratePick" hidden></div><div class="grid">{cards}</div>{EMPTY}<p class="nomatch" id="nomatch" hidden>No recipes match &ldquo;<span id="nmq"></span>&rdquo;. Try another word.</p>{pages}</main>{SB_JS}{ADD_HTML}{RATE_JS}{SEARCH_JS}{RATEF_JS}{TAGS_JS}{CART_HTML}<script>
if('serviceWorker' in navigator){{navigator.serviceWorker.register('sw.js',{{updateViaCache:'none'}}).then(r=>{{r.update();document.addEventListener('visibilitychange',()=>{{if(!document.hidden)r.update()}})}});let R0=!!navigator.serviceWorker.controller;navigator.serviceWorker.addEventListener('controllerchange',()=>{{if(R0)location.reload();R0=true}})}}
window.addEventListener('hashchange',function(){{window.scrollTo(0,0)}});
</script></body></html>''')
print(f'Built index.html with {len(R)} recipe(s)')

# ---- PWA assets (manifest, icons, service worker) ----
import os, hashlib
from PIL import Image, ImageDraw
TERRA, CREAM, TAN, LINE = (181, 84, 45), (251, 245, 236), (240, 214, 184), (214, 160, 120)
def draw_icon(size, maskable=False):
    from PIL import Image
    src = Image.open("icon-source.png").convert("RGB")
    if not maskable: return src.resize((size, size), Image.LANCZOS)
    bg = src.getpixel((src.width//2, 10)); out = Image.new("RGB", (size, size), bg)
    inner = int(size*0.8); out.paste(src.resize((inner, inner), Image.LANCZOS), ((size-inner)//2,)*2); return out

os.makedirs("icons", exist_ok=True)
if not os.path.exists("icon-source.png"):
    import subprocess, sys; subprocess.run([sys.executable, "make_icon.py"], check=True)
for s in (180, 192, 512): draw_icon(s).save(f"icons/icon-{s}.png")
for s in (192, 512): draw_icon(s, True).save(f"icons/icon-maskable-{s}.png")
TC = CFG.get("theme_color") or "#faf8f5"
json.dump({"name": (FAMILY + " " + APP_NAME).strip(), "short_name": SHORT_NAME,
  "description": "Our family's favorite recipes",
  "id": "./", "start_url": "./", "scope": "./", "display": "standalone",
  "theme_color": TC, "background_color": TC,
  "icons": [{"src": f"icons/icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png", "purpose": "any"} for s in (192, 512)] +
           [{"src": f"icons/icon-maskable-{s}.png", "sizes": f"{s}x{s}", "type": "image/png", "purpose": "maskable"} for s in (192, 512)]},
  open("manifest.webmanifest", "w"), indent=2)
assets = ["./", "recipes.json", "manifest.webmanifest"] + [f"icons/{f}" for f in sorted(os.listdir("icons")) if f.startswith("icon-")]  # images are cached on demand (cache-first), never precached
ver = hashlib.sha1(open("index.html", "rb").read() + json.dumps(assets).encode()).hexdigest()[:10]
open("sw.js", "w").write("""// Generated by build.py. Pages/data: network-first (new recipes show when online), cached copy offline.
// Images: not precached; cached on first view (cache-first, refreshed in the background).
const CACHE = 'recipes-%s';
const ASSETS = %s;
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))); });
self.addEventListener('activate', e => e.waitUntil(caches.keys()
  .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
const save = (req, res) => { if (res.ok) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(req, cp)); } return res; };
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (req.destination === 'image') {
    e.respondWith(caches.match(req).then(hit => { const net = fetch(req).then(r => save(req, r)).catch(() => hit); return hit || net; }));
  } else {
    e.respondWith(fetch(req, {cache: 'no-store'}).then(r => save(req, r))
      .catch(() => caches.match(req, {ignoreSearch: true}).then(h => h || caches.match('./'))));
  }
});
""" % (ver, json.dumps(assets)))
print("Built PWA assets: manifest.webmanifest, sw.js, icons/")
