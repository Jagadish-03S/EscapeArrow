export const $=s=>document.querySelector(s);
export function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),4000)}
export function modal(html){$('#modal').innerHTML=html;$('#modal').showModal()}
export const closeModal=()=>$('#modal').close();
export function pet(kind='cat'){const src=kind==='dog'?'https://images.unsplash.com/photo-1552053831-71594a27632d?w=480&q=80':'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=480&q=80';return `<div class="pet-photo ${kind}"><img src="${src}" alt="Real ${kind} companion" loading="lazy"></div>`}
export const coinIcon=()=>'<span class="wallet-icon coin-icon" aria-label="Gold coin">🪙</span>';
export const diamondIcon=()=>'<span class="wallet-icon diamond-icon" aria-label="Diamond">◆</span>';
export function bind(selector,fn){document.querySelectorAll(selector).forEach(el=>el.onclick=()=>Promise.resolve(fn(el)).catch(e=>toast(e.message)))}
export const fmt=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
