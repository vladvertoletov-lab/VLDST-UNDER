
const tg=window.Telegram?.WebApp;
tg?.ready(); tg?.expand(); tg?.setHeaderColor?.('#07070d'); tg?.setBackgroundColor?.('#07070d');
let token=localStorage.getItem('vldst_token');
const api=location.origin+'/api';
const state={me:null,tab:'home',cache:{},filters:{rarity:'ALL',inventory:'NEWEST'}};
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString('en-US');
const idk=()=>crypto?.randomUUID?.()||String(Date.now())+Math.random();
function haptic(type='light'){try{tg?.HapticFeedback?.impactOccurred(type)}catch{}}
async function req(path,opt={}){
  const headers={'Content-Type':'application/json',...(opt.headers||{})};
  if(token) headers.Authorization=`Bearer ${token}`;
  const r=await fetch(api+path,{...opt,headers});
  let d={}; try{d=await r.json()}catch{}
  if(!r.ok) throw Error(d.detail||'Something went wrong');
  return d;
}
async function auth(){
  if(token)return true;
  const init=tg?.initData;
  if(!init){renderError('Открой VLDST UNDERGROUND внутри Telegram.');return false}
  try{const d=await req('/auth/telegram',{method:'POST',body:JSON.stringify({init_data:init})});token=d.token;localStorage.setItem('vldst_token',token);return true}
  catch(e){renderError(e.message);return false}
}
function loading(){app.innerHTML=`<div class="loading"><div class="skel tall"></div><div class="skel"></div><div class="skel"></div><div class="skel"></div></div>`}
function renderError(msg){app.innerHTML=`<div class="error-box"><b>Connection error</b><p class="muted">${esc(msg)}</p><button class="btn" onclick="location.reload()">RETRY</button></div>`}
function toast(msg,type='ok'){const root=$('#toast-root');const el=document.createElement('div');el.className='toast '+type;el.textContent=msg;root.appendChild(el);setTimeout(()=>el.remove(),2800);if(type==='ok')haptic('light')}
function nav(){document.querySelectorAll('.bottom-nav button').forEach(b=>b.classList.toggle('active',b.dataset.tab===state.tab))}
async function refreshMe(){state.me=await req('/me');$('#balance').textContent=fmt(state.me.vld)}
async function load(key,path){if(!state.cache[key])state.cache[key]=await req(path);return state.cache[key]}
async function tab(t){state.tab=t;nav();loading();try{await refreshMe();({home,cases,games,quests,profile}[t]||home)()}catch(e){renderError(e.message)}}
function progress(p){return `<div class="progress"><span style="width:${Math.max(0,Math.min(100,p))}%"></span></div>`}
function stats(){
 const m=state.me; const pct=Math.min(100,Math.round((m.xp%Math.max(1,(m.level||1)*1000))/Math.max(1,(m.level||1)*1000)*100));
 return `<div class="stats"><div class="stat"><small>LEVEL</small><b>${m.level}</b></div><div class="stat"><small>XP</small><b>${fmt(m.xp)}</b></div><div class="stat"><small>ENERGY</small><b>${m.energy}</b></div><div class="stat"><small>SCRAP</small><b>${fmt(m.scrap)}</b></div></div>${progress(pct)}`;
}
async function home(){
 const m=state.me;
 app.innerHTML=`
 <section class="hero"><div class="eyebrow">SYSTEM ONLINE · SEASON 01</div><h1>ENTER THE<br>UNDERGROUND.</h1>
 <p>Your daily cyber loop: play, discover, collect, build your Vault.</p>
 <div class="hero-actions"><button class="btn" onclick="tab('cases')">CASE LAB</button><button class="btn secondary" onclick="tab('games')">PLAY GAME</button></div>${stats()}
 </section>
 <div class="section-head"><h2>Command center</h2><span>12 systems</span></div>
 <div class="quick-grid">
 ${quick('Vault','Inventory, showcase & slots','vault','▣')}
 ${quick('Collections','Progress & completion rewards','collections','◇')}
 ${quick('Guild','Crew, rank & contribution','guild','⌁')}
 ${quick('Events','Live events & global goals','events','✦')}
 ${quick('Season Pass','50-level progression','season','↗')}
 ${quick('Stars Shop','Premium cosmetics','shop','✧')}
 ${quick('Achievements','100+ milestones & titles','achievements','★')}
 ${quick('Transactions','Complete economy ledger','transactions','≋')}
 ${quick('Market','Buy & sell artifacts','market','◇')}
 ${quick('Craft Lab','Recipes & crafting','craft','⚒')}
 ${quick('Fusion','Fuse 3 artifacts','fusion','✦')}
 ${quick('Promo','Redeem a promo code','promo','%')}
 </div>
 <div class="section-head"><h2>Daily pulse</h2><span>Live</span></div>
 <div class="card pulse-card"><div><span class="label">STREAK</span><b>${m.streak||0} DAYS</b></div><div><span class="label">REFERRAL</span><b class="cyan">${esc(m.referral_code||'—')}</b></div><div><span class="label">VLD</span><b class="gold">${fmt(m.vld)}</b></div></div>`;
}
function quick(title,sub,fn,icon){return `<button class="card quick" onclick="${fn}()"><span class="quick-icon">${icon}</span><strong>${title}</strong><small>${sub}</small><span class="arrow">›</span></button>`}
async function cases(){
 const a=await load('cases','/cases');
 app.innerHTML=`<div class="page-hero"><div><div class="eyebrow">CASE LAB</div><h1>Choose your capsule.</h1><p>Transparent odds. VLD only. No paid random chance.</p></div></div>
 <div class="chip-row"><button class="chip active">ALL CAPSULES</button><button class="chip" onclick="openModalBy('pity')">PITY RULES</button><button class="chip" onclick="openModalBy('odds')">ODDS</button></div>
 <div class="cards">${a.map(x=>`<article class="card case-card"><div class="case-art"><img src="${esc(x.image)}" loading="lazy"></div><div class="case-body"><div class="row"><h3>${esc(x.name)}</h3><span class="price">${fmt(x.price)} VLD</span></div><div class="rarities">${Object.entries(x.weights||{}).map(([k,v])=>`<span><b>${k}</b> ${(v*100).toFixed(v<.01?2:1)}%</span>`).join('')}</div><button class="mini-btn primary" onclick="openCase(${x.id})">OPEN CAPSULE</button></div></article>`).join('')}</div>`;
}
async function openCase(id){
 const c=(await load('cases','/cases')).find(x=>x.id===id);
 showModal(`<div class="modal-head"><div><span class="eyebrow">CASE LAB</span><h2>${esc(c?.name||'CAPSULE')}</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="opening"><img src="${esc(c?.image||'')}"><div class="scanline"></div><div class="opening-status">SYSTEM CHECK · READY</div><button class="btn full" onclick="confirmCase(${id})">CONFIRM · ${fmt(c?.price)} VLD</button></div>`);
}
async function confirmCase(id){
 const box=$('.opening');if(!box)return;
 box.classList.add('scanning');$('.opening-status').textContent='SCANNING · SERVER ROLL';
 try{const d=await req(`/cases/${id}/open`,{method:'POST',headers:{'Idempotency-Key':idk()}});await new Promise(r=>setTimeout(r,850));haptic('medium');
 $('.opening-status').innerHTML=`<span class="rarity-title ${String(d.rarity||'RARE').toLowerCase()}">${esc(d.rarity||'RARE')}</span>`;
 box.innerHTML=`<div class="reward-reveal"><img src="${esc(d.image||'/assets/items/item_001.svg')}"><span class="rarity-title ${String(d.rarity||'RARE').toLowerCase()}">${esc(d.rarity||'RARE')}</span><h2>${esc(d.item_name||'NEW ARTIFACT')}</h2><p class="muted">Added to Vault · collection progress updated</p><div class="reward-actions"><button class="btn" onclick="closeModal();vault()">VAULT</button><button class="btn secondary" onclick="closeModal();tab('cases')">AGAIN</button></div></div>`;
 await refreshMe(); state.cache.inventory=null;
 }catch(e){closeModal();toast(e.message,'error')}
}
async function games(){
 const a=await load('games','/games');
 app.innerHTML=`<div class="page-hero"><div><div class="eyebrow">GAME HUB</div><h1>Skill over luck.</h1><p>${state.me.energy} Energy available · rewards are gameplay-based.</p></div></div><div class="game-banner"><b>10 ARCADE SYSTEMS</b><span>Daily score · XP · VLD</span></div><div class="cards">${a.map(x=>`<article class="card game-card"><div class="game-art"><img src="/assets/games/game_${String(x.id).padStart(2,'0')}.svg" loading="lazy"></div><div class="game-meta"><h3>${esc(x.name)}</h3><span>${x.energy_cost} ENERGY</span></div><button class="mini-btn primary" onclick="play(${x.id},'${esc(x.code)}')">PLAY RUN</button></article>`).join('')}</div>`;
}
async function play(id,code){
 try{const s=await req(`/games/${id}/start`,{method:'POST'});const g=code.toLowerCase();if(g.includes('reaction'))return reaction(id,s);if(g.includes('memory'))return memory(id,s);if(g.includes('aim'))return aim(id,s);return quickGame(id,s)}
 catch(e){toast(e.message,'error')}
}
function gameModal(title,html){showModal(`<div class="modal-head"><div><span class="eyebrow">ARCADE RUN</span><h2>${title}</h2></div><button class="close" onclick="closeModal()">×</button></div>${html}`)}
async function finishGame(id,nonce,score){
 try{const d=await req(`/games/${id}/finish`,{method:'POST',body:JSON.stringify({nonce,score})});haptic('medium');gameModal('RUN COMPLETE',`<div class="result-hero"><span class="label">FINAL SCORE</span><strong>${fmt(d.score)}</strong><div class="reward-line">+${fmt(d.vld)} VLD · +${d.xp} XP</div></div><button class="btn full" onclick="closeModal();tab('games')">BACK TO HUB</button>`);await refreshMe()}
 catch(e){toast(e.message,'error')}
}
function reaction(id,s){gameModal('REACTION',`<p class="muted">Wait for the signal. Tap only when it turns live.</p><div id="react-zone" class="tap-zone"><button id="react-btn" class="btn">WAIT…</button></div>`);let start=0;const delay=800+Math.random()*1800;setTimeout(()=>{const b=$('#react-btn');if(!b)return;b.textContent='TAP NOW';start=performance.now();b.onclick=()=>finishGame(id,s.nonce,Math.max(100,Math.min(10000,10000-Math.floor((performance.now()-start)*8))))},delay)}
function memory(id,s){const seq=Array.from({length:5},()=>Math.floor(Math.random()*4));gameModal('MEMORY',`<p class="muted">Observe, then reproduce the signal sequence.</p><div id="memory-grid" class="memory-grid">${[0,1,2,3].map(i=>`<button data-i="${i}">${i+1}</button>`).join('')}</div><p id="memory-status" class="small muted">WATCHING…</p>`);let idx=0;const bs=[...document.querySelectorAll('#memory-grid button')];bs.forEach(b=>b.disabled=true);seq.forEach((v,i)=>setTimeout(()=>{bs[v].classList.add('flash');setTimeout(()=>bs[v].classList.remove('flash'),240)},500+i*500));setTimeout(()=>{bs.forEach(b=>{b.disabled=false;b.onclick=()=>{if(+b.dataset.i!==seq[idx])return finishGame(id,s.nonce,0);idx++;if(idx===seq.length)finishGame(id,s.nonce,9000)}});$('#memory-status').textContent='YOUR TURN'},800+seq.length*500)}
function aim(id,s){gameModal('AIM',`<p class="muted">Hit six targets. Accuracy and speed matter.</p><div id="aim-zone" class="tap-zone"></div><div id="aim-count" class="small muted">0 / 6</div>`);let hit=0,start=performance.now(),zone=$('#aim-zone');function spawn(){const b=document.createElement('button');b.className='game-target';b.style.left=(8+Math.random()*78)+'%';b.style.top=(8+Math.random()*72)+'%';b.onclick=()=>{hit++;b.remove();$('#aim-count').textContent=`${hit} / 6`;if(hit>=6)finishGame(id,s.nonce,Math.max(1000,10000-Math.floor((performance.now()-start)*2)));else spawn()};zone.appendChild(b)}spawn();setTimeout(()=>{if(hit<6)finishGame(id,s.nonce,hit*1300)},8000)}
function quickGame(id,s){gameModal('SIGNAL HUNT',`<div class="game-play"><button id="quick-tap" class="btn" style="width:230px;height:70px">TAP TO SCORE</button></div><p class="muted center">Build score, then lock your run.</p>`);let n=0;$('#quick-tap').onclick=()=>{n+=Math.floor(400+Math.random()*850);if(n>7000)finishGame(id,s.nonce,n)}}
async function quests(){
 const a=await load('quests','/quests');
 app.innerHTML=`<div class="page-hero"><div><div class="eyebrow">OPERATIONS</div><h1>Mission control.</h1><p>Daily, weekly and seasonal progression.</p></div></div><div class="segmented"><button class="active">DAILY</button><button onclick="showQuestInfo('weekly')">WEEKLY</button><button onclick="showQuestInfo('season')">SEASON</button></div><div class="quest-list">${a.map(x=>`<article class="card quest"><div class="qtop"><div><span class="quest-type">${esc(x.period)}</span><h3>${esc(x.title)}</h3></div><span class="reward">+${fmt(x.reward_vld)} VLD</span></div><p>${esc(x.description)}</p>${progress(100)}<div class="quest-foot"><span>Target ${x.target} · +${x.reward_xp} XP</span><button class="mini-btn" onclick="claim(${x.id})">CLAIM</button></div></article>`).join('')}</div>`;
}
async function claim(id){try{const d=await req(`/quests/${id}/claim`,{method:'POST',headers:{'Idempotency-Key':idk()}});toast(`+${fmt(d.reward_vld)} VLD · +${d.reward_xp} XP`);state.cache.quests=null;await refreshMe();quests()}catch(e){toast(e.message,'error')}}
async function profile(){
 const [p,inv]=await Promise.all([req('/profile'),req('/inventory')]);
 app.innerHTML=`<section class="profile-cover card"><div class="profile-hero"><div class="avatar">${tg?.initDataUnsafe?.user?.photo_url?`<img src="${esc(tg.initDataUnsafe.user.photo_url)}">`:'V'}</div><div class="profile-copy"><span class="eyebrow">UNDERGROUND ID</span><h1>${esc(p.user||'VLDST PLAYER')}</h1><p>LEVEL ${p.level} · ${fmt(p.xp)} XP</p>${progress(Math.min(100,Math.round((p.xp%Math.max(1,p.level*1000))/(p.level*1000)*100)))}</div></div><div class="profile-stats"><span><b>${inv.length}</b> ITEMS</span><span><b>${p.achievements||0}</b> ACHIEVEMENTS</span><span><b>${state.me.streak||0}</b> STREAK</span></div></section>
 <div class="section-head"><h2>Player systems</h2><span>Open</span></div>
 <div class="menu-grid">
 ${menu('VAULT','Inventory · slots · showcase','vault','▣')}${menu('COLLECTIONS','20 collections · rewards','collections','◇')}${menu('GUILD','Crew · rank · contribution','guild','⌁')}${menu('EVENTS','Live events · global goals','events','✦')}${menu('SEASON PASS','50 levels · 30 days','season','↗')}${menu('STARS SHOP','Premium · cosmetics','shop','✧')}${menu('ACHIEVEMENTS','Milestones · titles','achievements','★')}${menu('TRANSACTIONS','VLD · items · history','transactions','≋')}${menu('REFERRALS','Invite active players','referrals','⤴')}${menu('LEADERBOARD','Global rankings','leaderboard','№')}${menu('CUSTOMIZATION','Frame · background · theme','customize','◌')}${menu('NOTIFICATIONS','Updates & alerts','notifications','◉')}</div>`;
}
function menu(t,sub,fn,icon){return `<button class="system-card card" onclick="${fn}()"><span class="system-icon">${icon}</span><span><strong>${t}</strong><small>${sub}</small></span><b>›</b></button>`}
async function vault(){
 const a=await load('inventory','/inventory'); const show=await req('/vault/showcase');
 showModal(`<div class="modal-head"><div><span class="eyebrow">VAULT</span><h2>Artifact storage</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="vault-head"><div><b>${a.length}</b><small>VISIBLE ITEMS</small></div><div>${progress(Math.min(100,a.length/500*100))}<small>VAULT CAPACITY · 500 SLOTS</small></div></div><div class="chip-row">${['ALL','COMMON','RARE','EPIC','LEGENDARY','MYTHIC','SECRET'].map(r=>`<button class="chip ${state.filters.rarity===r?'active':''}" onclick="vaultFilter('${r}')">${r}</button>`).join('')}</div><div class="inventory-grid">${a.filter(x=>state.filters.rarity==='ALL'||x.rarity===state.filters.rarity).map(x=>`<article class="item-card"><img src="${esc(x.image)}" loading="lazy"><div class="item-info"><strong>${esc(x.name)}</strong><span class="rarity ${esc(x.rarity)}">${esc(x.rarity)} · LV ${x.level}</span><small>${fmt(x.value)} VLD · ${esc(x.collection)}</small><div class="item-actions"><button onclick="toggleShowcase(${x.inventory_id})">${show.some(z=>z.inventory_id===x.inventory_id)?'REMOVE':'SHOWCASE'}</button><button onclick="upgradeItem(${x.inventory_id})">UPGRADE</button><button onclick="recycleItem(${x.inventory_id})">RECYCLE</button></div></div></article>`).join('')||'<div class="empty">No artifacts match this filter.</div>'}</div><div class="showcase-strip"><span>SHOWCASE · ${show.length}/6</span><small>Your selected artifacts appear on your public profile.</small></div>`);
}
function vaultFilter(r){state.filters.rarity=r;state.cache.inventory=null;vault()}
async function toggleShowcase(id){try{const cur=await req('/vault/showcase');let ids=cur.map(x=>x.inventory_id);ids=ids.includes(id)?ids.filter(x=>x!==id):ids.length<6?[...ids,id]:ids;await req('/vault/showcase',{method:'POST',body:JSON.stringify({inventory_ids:ids}),headers:{'Idempotency-Key':idk()}});state.cache.inventory=null;toast('Showcase updated');vault()}catch(e){toast(e.message,'error')}}
async function upgradeItem(id){try{await req(`/inventory/${id}/upgrade`,{method:'POST',headers:{'Idempotency-Key':idk()}});state.cache.inventory=null;await refreshMe();toast('Artifact upgraded');vault()}catch(e){toast(e.message,'error')}}
async function recycleItem(id){if(!confirm('Recycle this artifact?'))return;try{await req(`/inventory/${id}/recycle`,{method:'POST',headers:{'Idempotency-Key':idk()}});state.cache.inventory=null;await refreshMe();toast('Artifact recycled');vault()}catch(e){toast(e.message,'error')}}
async function collections(){
 const c=await load('collections','/collections');showModal(`<div class="modal-head"><div><span class="eyebrow">COLLECTIONS</span><h2>Collection index</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="collection-list">${c.map(x=>`<article class="collection-card"><div class="collection-art"><img src="/assets/ui/void_night.svg"></div><div class="collection-info"><div class="row"><h3>${esc(x.name)}</h3><b>${x.owned}/${x.total}</b></div><p>${esc(x.description)}</p>${progress(x.progress)}<div class="milestones">${[25,50,75,100].map(m=>`<button class="chip ${x.milestones[String(m)]?'active':''}" ${x.milestones[String(m)]?'':'disabled'} onclick="claimCollection(${x.id},${m})">${m}% · CLAIM</button>`).join('')}</div></div></article>`).join('')}</div>`);
}
async function claimCollection(id,m){try{const d=await req(`/collections/${id}/claim/${m}`,{method:'POST',headers:{'Idempotency-Key':idk()}});state.cache.collections=null;await refreshMe();toast(`+${fmt(d.vld)} VLD · collection reward`);collections()}catch(e){toast(e.message,'error')}}
async function guild(){
 const d=await load('guild','/guild');
 if(!d.guild){const gs=await req('/guilds');showModal(`<div class="modal-head"><div><span class="eyebrow">GUILD NETWORK</span><h2>Build your crew.</h2></div><button class="close" onclick="closeModal()">×</button></div><button class="btn full" onclick="createGuild()">CREATE GUILD</button><div class="section-head"><h3>Top guilds</h3></div><div class="leader-list">${gs.map(g=>`<div class="leader-row"><span class="rank">#</span><span class="leader-avatar">${esc(g.tag[0])}</span><div><b>${esc(g.name)}</b><small>${esc(g.tag)} · ${g.members}/${g.max_members} MEMBERS</small></div><button class="mini-btn primary" onclick="joinGuild(${g.id})">JOIN</button></div>`).join('')||'<div class="empty">No guilds yet.</div>'}</div>`);return}
 const g=d.guild;showModal(`<div class="modal-head"><div><span class="eyebrow">GUILD NETWORK</span><h2>Your crew</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="guild-banner"><div class="guild-logo">${esc(g.tag)}</div><div><h2>${esc(g.name)}</h2><span>${esc(g.tag)} · LEVEL ${g.level} · ${g.members}/${g.max_members}</span></div><div class="guild-role">${esc(g.role)}</div></div><div class="guild-grid"><div class="stat-card"><b>${fmt(g.xp)}</b><small>GUILD XP</small></div><div class="stat-card"><b>${g.members}</b><small>MEMBERS</small></div><div class="stat-card"><b>#—</b><small>RANK</small></div></div><div class="menu-list"><button class="menu-item" onclick="leaderboardGuild()"><strong>GUILD LEADERBOARD</strong><span>›</span></button>${g.role!=='owner'?'<button class="menu-item" onclick="leaveGuild()"><strong>LEAVE GUILD</strong><span>›</span></button>':''}</div>`);
}
async function createGuild(){const name=prompt('Guild name');if(!name)return;const tag=prompt('Guild tag (2-12 letters)');if(!tag)return;try{await req('/guild/create',{method:'POST',body:JSON.stringify({name,tag})});state.cache.guild=null;toast('Guild created');guild()}catch(e){toast(e.message,'error')}}
async function joinGuild(id){try{await req('/guild/join',{method:'POST',body:JSON.stringify({guild_id:id})});state.cache.guild=null;toast('Welcome to the Guild');guild()}catch(e){toast(e.message,'error')}}
async function leaveGuild(){if(!confirm('Leave this Guild?'))return;try{await req('/guild/leave',{method:'POST'});state.cache.guild=null;toast('Guild left');guild()}catch(e){toast(e.message,'error')}}
function showToastSafe(s){toast(s,'ok')}
async function events(){const a=await load('events','/events');showModal(`<div class="modal-head"><div><span class="eyebrow">EVENT GRID</span><h2>Live operations</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="event-list">${a.map(x=>`<article class="event-card"><img src="${esc(x.banner||'/assets/ui/void_night.svg')}"><div class="event-content"><span class="event-status">${x.status}</span><h3>${esc(x.name)}</h3><p>${esc(x.description)}</p><div class="event-goal"><span>GLOBAL</span><b>${fmt(x.global_progress||0)} / ${fmt(x.goal||0)}</b></div>${x.joined?`<div>${progress(x.goal?x.progress/x.goal*100:0)}<small class="muted">PERSONAL ${x.progress}</small></div>`:''}<button class="mini-btn primary" onclick="eventAction(${x.id},'${x.joined?'progress':'join'}')">${x.joined?'RUN EVENT':'ENTER EVENT'}</button>${x.joined&&x.goal&&x.global_progress>=x.goal&&!x.reward_claimed?`<button class="mini-btn" onclick="eventAction(${x.id},'claim')">CLAIM GLOBAL REWARD</button>`:''}</div></article>`).join('')||'<div class="empty">No events scheduled.</div>'}</div>`)}
async function eventAction(id,action){try{if(action==='join')await req(`/events/${id}/join`,{method:'POST'});else if(action==='progress'){toast('Event progress is earned through verified gameplay.');return}else {const d=await req(`/events/${id}/claim`,{method:'POST',headers:{'Idempotency-Key':idk()}});toast(`+${fmt(d.vld)} VLD · event reward`)}state.cache.events=null;await refreshMe();events()}catch(e){toast(e.message,'error')}}
async function season(){const a=await load('seasons','/seasons');const s=a[0];if(!s){toast('No active season','error');return}showModal(`<div class="modal-head"><div><span class="eyebrow">SEASON PASS</span><h2>${esc(s.name)}</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="season-hero"><div class="season-level"><span>LEVEL</span><strong>${s.level}</strong><small>/ ${s.levels}</small></div>${progress(s.level/s.levels*100)}<p class="muted">Season XP ${fmt(s.xp)} · claim each level once.</p></div><div class="season-track">${s.rewards.slice(0,20).map(r=>`<button class="season-node ${s.claimed_levels.includes(r.level)?'claimed':''}" onclick="claimSeason(${s.id},${r.level})"><b>${r.level}</b><span>${r.level%10===0?'★':'VLD'}</span><small>${s.claimed_levels.includes(r.level)?'CLAIMED':`+${fmt(r.vld)}`}</small></button>`).join('')}</div><div class="premium-callout"><div><span class="eyebrow">PREMIUM PASS</span><h3>Cosmetic-first progression</h3><p>Premium is optional and never required for the core game.</p></div><button class="btn" onclick="shop()">VIEW STARS</button></div>`)}
async function claimSeason(id,level){try{const d=await req(`/seasons/${id}/claim`,{method:'POST',body:JSON.stringify({level}),headers:{'Idempotency-Key':idk()}});state.cache.seasons=null;await refreshMe();toast(`Level ${level} claimed · +${fmt(d.vld)} VLD`);season()}catch(e){toast(e.message,'error')}}
async function shop(){
 const a=await load('shop','/shop');showModal(`<div class="modal-head"><div><span class="eyebrow">STARS MARKET</span><h2>Cosmetics only.</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="stars-balance"><span>TELEGRAM STARS</span><b>★</b><small>Digital goods · voluntary · no random paid outcomes</small></div><div class="shop-grid">${a.map(x=>`<article class="shop-card"><img src="${esc(x.image)}" loading="lazy"><span class="shop-cat">${esc(x.category)}</span><h3>${esc(x.name)}</h3><p>${esc(x.description)}</p><button class="mini-btn primary" onclick="buyStars(${x.id},${x.stars})">★ ${x.stars} STARS</button></article>`).join('')}</div>`);
}
async function buyStars(id,stars){try{const d=await req('/shop/purchase',{method:'POST',body:JSON.stringify({product_id:id})});if(d.invoice_url&&tg?.openInvoice){tg.openInvoice(d.invoice_url,(status)=>{if(status==='paid'){state.cache.shop=null;toast('Payment confirmed · item delivered');refreshMe()}else if(status==='cancelled')toast('Payment cancelled','error');else if(status==='failed')toast('Payment failed','error')})}else if(d.invoice_url){window.location.href=d.invoice_url}else toast('Invoice created');}catch(e){toast(e.message,'error')}}
async function achievements(){const a=await req('/achievements');const unlocked=a.filter(x=>x.unlocked).length;showModal(`<div class="modal-head"><div><span class="eyebrow">ACHIEVEMENT MATRIX</span><h2>Milestones & titles</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="achievement-summary"><strong>${unlocked}</strong><span>UNLOCKED / ${a.length}</span><div class="title-chip">CURRENT TITLE · ${esc(state.me.title||'NEWCOMER')}</div></div><div class="achievement-list">${a.map(x=>`<div class="achievement-row ${x.unlocked?'':'read'}"><span class="achievement-icon">★</span><div><b>${esc(x.name)}</b><small>${esc(x.category)} · +${fmt(x.reward_vld)} VLD · +${x.reward_xp} XP</small>${x.title?`<span class="title-chip">TITLE · ${esc(x.title)}</span>`:''}</div><span>${x.unlocked?'✓':'·'}</span></div>`).join('')}</div><div class="title-wall"><span class="eyebrow">TITLE WALL</span><div>${['NEWCOMER',...a.map(x=>x.title).filter(Boolean)].filter((x,i,arr)=>arr.indexOf(x)===i).map(x=>`<button class="title-pill ${x===(state.me.title||'NEWCOMER')?'selected':''}" onclick="selectTitle('${esc(x)}')">${esc(x)}</button>`).join('')}</div></div>`)}
async function selectTitle(title){try{await req('/profile/title',{method:'POST',body:JSON.stringify({title})});state.me.title=title;toast(`Title selected: ${title}`);achievements()}catch(e){toast(e.message,'error')}}
async function transactions(){
 const a=await load('transactions','/transactions');showModal(`<div class="modal-head"><div><span class="eyebrow">ECONOMY LEDGER</span><h2>Transactions</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="ledger-head"><div><span>VLD BALANCE</span><b>${fmt(state.me.vld)}</b></div><div><span>ENTRIES</span><b>${a.length}</b></div></div><div class="ledger">${a.map(x=>`<div class="ledger-row"><span class="tx-icon">${String(x.amount)>=0?'+':'−'}</span><div><b>${esc(x.kind)}</b><small>${esc(x.reference||'SYSTEM')} · ${x.created_at?new Date(x.created_at).toLocaleString():''}</small></div><strong class="${Number(x.amount)>=0?'green':'danger'}">${Number(x.amount)>=0?'+':''}${fmt(x.amount)} ${esc(x.currency)}</strong></div>`).join('')||'<div class="empty">No transactions yet.</div>'}</div>`);
}
async function referrals(){const d=await load('referrals','/referrals');showModal(`<div class="modal-head"><div><span class="eyebrow">NETWORK</span><h2>Referrals</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="referral-hero"><span>YOUR CODE</span><strong>${esc(d.code)}</strong><button class="btn full" onclick="copyText('${esc(d.link)}')">COPY INVITE LINK</button></div><div class="ref-milestones"><div><b>0</b><span>REGISTERED</span></div><div><b>3</b><span>LEVEL 3</span></div><div><b>5</b><span>LEVEL 5</span></div><div><b>10</b><span>ACTIVE</span></div></div><p class="muted">Rewards unlock when invited players actually use the game.</p>`)}
async function leaderboardGuild(){await leaderboard()}
async function leaderboard(){const a=await load('leaderboard','/leaderboard');showModal(`<div class="modal-head"><div><span class="eyebrow">RANKING NETWORK</span><h2>Global leaderboard</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="leaderboard-tabs"><button class="active">GLOBAL</button><button>WEEKLY</button><button>SEASON</button></div><div class="leader-list">${a.slice(0,30).map(x=>`<div class="leader-row ${x.nickname===state.me.user?'me':''}"><span class="rank">#${x.rank}</span><span class="leader-avatar">${esc((x.nickname||'V')[0])}</span><div><b>${esc(x.nickname)}</b><small>LEVEL ${x.level} · ${fmt(x.xp)} XP</small></div><strong>${fmt(x.xp)}</strong></div>`).join('')}</div>`)}
async function notifications(){const a=await load('notifications','/notifications');showModal(`<div class="modal-head"><div><span class="eyebrow">SIGNAL FEED</span><h2>Notifications</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="notification-list">${a.map(x=>`<div class="notification ${x.read?'read':''}"><span>◉</span><div><b>${esc(x.title)}</b><p>${esc(x.body)}</p></div></div>`).join('')||'<div class="empty">You are all caught up.</div>'}</div>`)}
function customize(){showModal(`<div class="modal-head"><div><span class="eyebrow">IDENTITY LAB</span><h2>Customize profile</h2></div><button class="close" onclick="closeModal()">×</button></div><div class="custom-grid">${['FRAME','BACKGROUND','TITLE','BADGE','EFFECT','THEME'].map((x,i)=>`<button class="custom-card" onclick="toast('${x} selector opened')"><span>${['◌','◈','★','◇','✦','⌁'][i]}</span><b>${x}</b><small>Preview & equip</small></button>`).join('')}</div>`)}
function showQuestInfo(type){toast(`${type.toUpperCase()} operations are server-configured.`)}
function openModalBy(kind){if(kind==='pity')showModal(`<div class="modal-head"><h2>Pity protocol</h2><button class="close" onclick="closeModal()">×</button></div><div class="info-card"><b>EPIC+</b><span>Guaranteed after 10 openings without EPIC+.</span><b>LEGENDARY+</b><span>Guaranteed after 20 openings without LEGENDARY+.</span><small>Pity counters are tracked server-side and shown before opening.</small></div>`);else showModal(`<div class="modal-head"><h2>Transparent odds</h2><button class="close" onclick="closeModal()">×</button></div><div class="info-card"><span>COMMON · 55%</span><span>RARE · 28%</span><span>EPIC · 12%</span><span>LEGENDARY · 4%</span><span>MYTHIC · 0.9%</span><span>SECRET · 0.1%</span></div>`)}
async function copyText(v){try{await navigator.clipboard.writeText(v);toast('Invite link copied')}catch{toast('Copy unavailable — hold to copy','error')}}
async function market(){
 const a=await load('market','/market');
 showModal(`<div class="modal-head"><div><span class="eyebrow">MARKET</span><h2>Artifact Exchange</h2></div><button class="close" onclick="closeModal()">×</button></div><p class="muted">Player listings · 5% platform fee on completed sales.</p><div class="inventory-grid">${a.map(x=>`<article class="item-card"><img src="${esc(x.image)}" loading="lazy"><div class="item-info"><strong>${esc(x.name)}</strong><span class="rarity ${esc(x.rarity)}">${esc(x.rarity)} · LV ${x.level}</span><small>${fmt(x.price)} VLD · ${esc(x.seller)}</small><div class="item-actions"><button onclick="buyListing(${x.id})">BUY</button></div></div></article>`).join('')||'<div class="empty">No active listings.</div>'}</div>`)
}
async function buyListing(id){try{const d=await req(`/market/${id}/buy`,{method:'POST',headers:{'Idempotency-Key':idk()}});state.cache.market=null;await refreshMe();toast(`Bought for ${fmt(d.price)} VLD`);market()}catch(e){toast(e.message,'error')}}
async function craft(){
 const recipes=await load('recipes','/craft/recipes');
 showModal(`<div class="modal-head"><div><span class="eyebrow">CRAFT LAB</span><h2>Build artifacts</h2></div><button class="close" onclick="closeModal()">×</button></div><p class="muted">Select a recipe, then choose the required number of Vault items.</p><div class="menu-list">${recipes.map(r=>`<button class="menu-item" onclick="runCraft(${r.id},${Number(r.requirements?.items||0)})"><strong>${esc(r.name)}</strong><span>${fmt(r.vld_cost)} VLD · ${fmt(r.scrap_cost)} SCRAP · ${Number(r.requirements?.items||0)} ITEMS ›</span></button>`).join('')||'<div class="empty">No recipes configured.</div>'}</div>`)
}
async function runCraft(recipeId,count){
 const inv=await load('inventory','/inventory'); const selected=inv.slice(0,count).map(x=>x.inventory_id);
 if(count && selected.length<count){toast('Not enough artifacts','error');return}
 try{await req('/craft',{method:'POST',body:JSON.stringify({recipe_id:recipeId,inventory_ids:selected}),headers:{'Idempotency-Key':idk()}});state.cache.inventory=null;state.cache.recipes=null;await refreshMe();toast('Artifact crafted');craft()}catch(e){toast(e.message,'error')}
}
async function fusion(){
 const inv=await load('inventory','/inventory');
 const groups=['COMMON','RARE','EPIC'];
 showModal(`<div class="modal-head"><div><span class="eyebrow">FUSION CORE</span><h2>Fuse 3 artifacts</h2></div><button class="close" onclick="closeModal()">×</button></div>${groups.map(r=>{const ids=inv.filter(x=>x.rarity===r).slice(0,3).map(x=>x.inventory_id);return `<div class="card" style="margin-bottom:10px"><b>${r} → ${r==='COMMON'?'RARE':r==='RARE'?'EPIC':'LEGENDARY'}</b><p class="muted">${ids.length}/3 available</p><button class="mini-btn primary" ${ids.length<3?'disabled':''} onclick='runFusion(${JSON.stringify(ids)})'>FUSE</button></div>`}).join('')}</div>`)
}
async function runFusion(ids){try{const d=await req('/fusion',{method:'POST',body:JSON.stringify({inventory_ids:ids}),headers:{'Idempotency-Key':idk()}});state.cache.inventory=null;await refreshMe();toast(`Fusion complete · ${d.rarity}`);fusion()}catch(e){toast(e.message,'error')}}
async function promo(){showModal(`<div class="modal-head"><div><span class="eyebrow">PROMO NETWORK</span><h2>Redeem code</h2></div><button class="close" onclick="closeModal()">×</button></div><input id="promo-code" class="input" maxlength="80" placeholder="ENTER CODE"><button class="btn full" onclick="redeemPromo()">REDEEM</button>`)}
async function redeemPromo(){const code=$('#promo-code')?.value?.trim();if(!code)return;try{const d=await req('/promo/redeem',{method:'POST',body:JSON.stringify({code}),headers:{'Idempotency-Key':idk()}});await refreshMe();toast(`+${fmt(d.vld)} VLD · +${d.xp} XP`);closeModal()}catch(e){toast(e.message,'error')}}
function showInventory(){vault()}
function shareProfile(){const text='I’m inside VLDST UNDERGROUND. Enter the underground.';const url=`https://t.me/share/url?url=${encodeURIComponent(location.href)}&text=${encodeURIComponent(text)}`;if(tg?.openTelegramLink)tg.openTelegramLink(url);else copyText(location.href)}
function showModal(html){$('#modal-root').innerHTML=`<div class="modal-backdrop" onclick="if(event.target===this)closeModal()"><div class="modal">${html}</div></div>`}
function closeModal(){$('#modal-root').innerHTML=''}
document.querySelectorAll('.bottom-nav button').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
(async()=>{if(await auth())await tab('home')})();
