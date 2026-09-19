const base=(window.ESCAPE_CONFIG?.apiBase||'').replace(/\/$/,'');
export const session={get token(){return sessionStorage.getItem('escape_token')||''},set token(v){v?sessionStorage.setItem('escape_token',v):sessionStorage.removeItem('escape_token')}};
export async function api(path,body,method){
 const r=await fetch(base+'/api'+path,{method:method||(body?'POST':'GET'),headers:{...(body instanceof FormData?{}:{'Content-Type':'application/json'}),...(session.token?{Authorization:'Bearer '+session.token}:{})},body:body?(body instanceof FormData?body:JSON.stringify(body)):undefined});
 const data=await r.json().catch(()=>({detail:'Server unavailable'}));
 if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Check the entered values');return data;
}
export const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
