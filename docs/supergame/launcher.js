(() => {
'use strict';
const $=s=>document.querySelector(s);
const grid=$('#gameGrid'),search=$('#searchGames'),chips=$('#filterChips'),count=$('#visibleCount'),empty=$('#emptyState'),favBtn=$('#favoritesToggle'),recent=$('#lastPlayed');
const genres=['All','Zombies','FPS','Open world','Strategy','RPG','Sandbox'];
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
const write=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch{}};
let games=[],genre='All',onlyFaves=false,faves=new Set(read('doug.launcher.favs.v1',[])),last=read('doug.launcher.recent.v1',null);
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e}
function makeChips(){chips.replaceChildren();for(const g of genres){const b=el('button','chip',g);b.type='button';b.setAttribute('aria-pressed',String(genre===g));b.onclick=()=>{genre=g;makeChips();render()};chips.append(b)}}
function card(game,index){
 const c=el('article','card'),art=el('div','art theme-'+game.theme);
 const badge=el('span','number',String(index+1).padStart(2,'0')+' / 15'),mark=el('span','mark',game.mark),illus=el('span','illustration','ORIGINAL STYLIZED CARD / '+game.subtitle);
 const star=el('button','star',faves.has(game.id)?'★':'☆');star.type='button';star.setAttribute('aria-label','Favorite '+game.title);star.setAttribute('aria-pressed',String(faves.has(game.id)));star.onclick=()=>{faves.has(game.id)?faves.delete(game.id):faves.add(game.id);write('doug.launcher.favs.v1',[...faves]);render()};art.append(badge,mark,illus,star);
 const copy=el('div','copy'),meta=el('div','meta');meta.append(el('span','',game.genre.toUpperCase()),el('span','',game.device));
 const stat=el('span','status '+game.status,({checked:'LINK LISTED',unverified:'UNVERIFIED',redirect:'REDIRECT WARNING',files:'GAME FILES REQUIRED'})[game.status]||'UNVERIFIED');
 const actions=el('div','card-actions'),go=el('a','launch','LAUNCH REAL SOURCE ↗');go.href=game.url;go.target='_blank';go.rel='noopener noreferrer';go.setAttribute('aria-label','Open '+game.title+' at its real source');go.onclick=()=>{last={id:game.id,title:game.title};write('doug.launcher.recent.v1',last);showRecent()};
 const cp=el('button','copylink','⧉');cp.type='button';cp.title='Copy link';cp.setAttribute('aria-label','Copy source link for '+game.title);cp.onclick=async()=>{try{await navigator.clipboard.writeText(game.url);cp.textContent='✓';setTimeout(()=>cp.textContent='⧉',1200)}catch{window.prompt('Copy source URL',game.url)}};actions.append(go,cp);
 copy.append(meta,el('h3','name',game.title),el('p','host',game.host),stat,el('p','note',game.note),actions);c.append(art,copy);return c;
}
function showRecent(){recent.textContent=last?'LAST OPENED: '+last.title+' (EXTERNAL TAB)':'SELECT A GAME TO LAUNCH FROM ITS ORIGINAL WEBSITE'}
function render(){const q=search.value.trim().toLowerCase(),display=games.filter(g=>(genre==='All'||g.genre===genre)&&(!onlyFaves||faves.has(g.id))&&[g.title,g.genre,g.host,g.subtitle].join(' ').toLowerCase().includes(q));grid.replaceChildren(...display.map(g=>card(g,games.indexOf(g))));count.textContent=display.length+' / '+games.length+' GAMES';empty.hidden=display.length>0;favBtn.setAttribute('aria-pressed',String(onlyFaves));favBtn.textContent=onlyFaves?'★ Favorites':'☆ Favorites';showRecent()}
search.addEventListener('input',render);favBtn.onclick=()=>{onlyFaves=!onlyFaves;render()};$('#resetFilters').onclick=()=>{genre='All';onlyFaves=false;search.value='';makeChips();render()};makeChips();
fetch('./catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(data=>{if(!Array.isArray(data)||data.length!==15||data.some(x=>!x.id||!x.url?.startsWith('https://')))throw Error('Invalid catalog');games=data;render()}).catch(e=>{grid.replaceChildren(el('div','empty','Catalog unavailable: '+e.message+'. Reload to retry.'));count.textContent='CATALOG OFFLINE'});
})();
