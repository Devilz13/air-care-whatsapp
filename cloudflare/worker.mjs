// Singapore-time pilot. No paid broadcast option and no WhatsApp sending code.
export const defaults = () => ({mode:'daily', times:['08:00'], hours:4, quiet:['22:00','08:00'], home:null, room:null});
export const HELP = 'Send STATUS, START, STOP, DAILY 08:00,18:00, EVERY 4 HOURS, QUIET 22:00 08:00, HOMES, HOME code, ROOM name, ALL, or SETTINGS. All times are Singapore time.';
const nowSeconds = () => Math.floor(Date.now()/1000);
const stmt = (db, sql, ...values) => db.prepare(sql).bind(...values);
const first = (db, sql, ...v) => stmt(db,sql,...v).first();
const run = (db, sql, ...v) => stmt(db,sql,...v).run();
const rows = async (db,sql,...v) => (await stmt(db,sql,...v).all()).results;
export function minute(value) {
  if(!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)) throw Error('Use a time such as 08:00.');
  return Number(value.slice(0,2))*60+Number(value.slice(3));
}
export const localMinute = ts => ((Math.floor(ts/60)+480)%1440+1440)%1440;
export function isQuiet(ts,p) {
  const m=localMinute(ts), a=minute(p.quiet[0]), b=minute(p.quiet[1]);
  return a<b ? m>=a&&m<b : m>=a||m<b;
}
export function nextDue(p,after) {
  let t=p.mode==='interval'?Math.ceil((after+p.hours*3600)/60)*60:Math.floor(after/60)*60+60;
  const times=p.times.map(minute);
  for(let i=0;i<2880;i++,t+=60) if(!isQuiet(t,p)&&(p.mode==='interval'||times.includes(localMinute(t)))) return t;
  throw Error('All report times are inside quiet hours. Change the report time or quiet hours.');
}
export function settings(p,active) {
  return `Reports ${active?'on':'off'}. ${p.mode==='daily'?'Daily '+p.times.join(','):'Every '+p.hours+' hours'}. Quiet ${p.quiet.join(' to ')}. Singapore time. Home: ${p.home||'all'}. Room: ${p.room||'all'}.`;
}
export function scheduleCommand(text,original) {
  const p=structuredClone(original);
  if(text.startsWith('DAILY ')) {
    const times=[...new Set(text.slice(6).replaceAll(' ','').split(','))].sort();
    if(times.length<1||times.length>4) throw Error('Set one to four times.');
    times.forEach(minute);p.mode='daily';p.times=times;
  } else if(text.startsWith('EVERY ')) {
    const m=/^EVERY (\d{1,2}) HOURS?$/.exec(text);
    if(!m||Number(m[1])<2||Number(m[1])>24) throw Error('Set 2 to 24 hours. Example: EVERY 4 HOURS.');
    p.mode='interval';p.hours=Number(m[1]);
  } else {
    const bits=text.split(' ');
    if(bits.length!==3||minute(bits[1])===minute(bits[2])) throw Error('Use different quiet start and end times.');
    p.quiet=bits.slice(1);
  }
  return p;
}
const metricInfo={pm25:['PM2.5','ug/m3',0,5000],humidity:['Humidity','%',0,100],temperature:['Temperature','C',-40,85],filter:['Filter remaining','%',0,100],tank_full:['Water tank full','',0,1]};
export function validateSnapshot(payload,now) {
  if(!Array.isArray(payload.devices)||payload.devices.length<1||payload.devices.length>20) throw Error('Invalid devices');
  const ids=new Set();
  for(const d of payload.devices) {
    for(const k of ['id','name','room']) if(typeof d[k]!=='string'||!d[k].length||d[k].length>60||/[\x00-\x1f]/.test(d[k])) throw Error('Invalid label');
    if(ids.has(d.id)) throw Error('Duplicate device');ids.add(d.id);
    if(!d.metrics||typeof d.metrics!=='object'||Array.isArray(d.metrics)) throw Error('Invalid metrics');
    for(const [k,r] of Object.entries(d.metrics)) {
      if(!metricInfo[k]||!r||!Number.isFinite(r.observed_at)||r.observed_at<=0||r.observed_at>now+60) throw Error('Invalid reading');
      if(r.value!==null&&(!Number.isFinite(r.value)||r.value<metricInfo[k][2]||r.value>metricInfo[k][3]||(k==='tank_full'&&![0,1].includes(r.value)))) throw Error('Invalid value');
    }
  }
  return payload;
}
export async function report(db,chat,now) {
  const user=await first(db,'SELECT * FROM users WHERE chat=?',chat),p=JSON.parse(user.prefs);
  const homes=await rows(db,'SELECT h.id,h.name,s.payload,s.received FROM access a JOIN homes h ON a.home=h.id LEFT JOIN snapshots s ON s.home=h.id WHERE a.chat=? ORDER BY h.name',chat);
  const lines=['AIR CARE | '+new Date((now+28800)*1000).toISOString().slice(0,16).replace('T',' ')+' SGT'];
  for(const h of homes) {
    if(p.home&&p.home!==h.id)continue;
    lines.push('\nHOME: '+h.name);
    if(!h.payload){lines.push('No device data. Ask your helper to check the connection.');continue;}
    const devices=JSON.parse(h.payload).devices.sort((a,b)=>a.room.localeCompare(b.room)||a.name.localeCompare(b.name));
    let room=null;
    for(const d of devices) {
      if(p.room&&d.room.toLowerCase()!==p.room)continue;
      if(room!==d.room){room=d.room;lines.push('ROOM: '+room);}
      lines.push(d.name);
      for(const [k,r] of Object.entries(d.metrics)) {
        const [label,unit]=metricInfo[k],age=now-r.observed_at;
        const value=r.value===null?'No data':age>900||now-h.received>900?'Old data. Check device.':k==='tank_full'?(r.value?'Yes. Empty the tank.':'No'):`${r.value} ${unit} (${Math.max(0,Math.floor(age/60))} min ago)`;
        lines.push(`${label}: ${value}`);
      }
    }
  }
  lines.push('\nPM2.5 is not PSI or AQI. Send HELP for commands.');
  const body=lines.join('\n');
  return body.length>3500?body.slice(0,3350)+'\nReport shortened. Send HOME code, then ROOM name, then STATUS.':body;
}
export async function send(env,chat,body,fetcher=fetch) {
  if(env.TELEGRAM_ENABLED!=='true') return false;
  if(!/^\d+:[A-Za-z0-9_-]+$/.test(env.TELEGRAM_BOT_TOKEN||'')) throw Error('Missing bot token');
  const response=await fetcher(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,{
    method:'POST',headers:{'Content-Type':'application/json'},redirect:'error',signal:AbortSignal.timeout(10000),
    body:JSON.stringify({chat_id:chat,text:body.slice(0,4000),allow_paid_broadcast:false,link_preview_options:{is_disabled:true}})
  });
  if(!response.ok||!(await response.json()).ok) throw Error('Telegram send failed');
  return true;
}
async function deliver(env,id,chat,body,fetcher) {
  try {const ok=await send(env,chat,body,fetcher);await run(env.DB,'UPDATE events SET state=? WHERE id=?',ok?'accepted':'disabled',id);}
  catch {await run(env.DB,'UPDATE events SET state=? WHERE id=?','unknown',id);}
  // Never retry uncertain sends automatically.
}
export async function handleUpdate(env,update,now=nowSeconds(),fetcher=fetch) {
  const m=update.message;
  if(!Number.isSafeInteger(update.update_id)||!m||m.chat?.type!=='private'||!Number.isSafeInteger(m.chat.id)||m.chat.id<=0||m.from?.id!==m.chat.id||!Number.isFinite(m.date)||m.date<now-300||m.date>now+60||typeof m.text!=='string'||m.text.length>256)return;
  const chat=String(m.chat.id), db=env.DB, user=await first(db,'SELECT * FROM users WHERE chat=?',chat);
  if(!user)return; // Operator enrollment only; no public household lookup.
  const id='tg:'+update.update_id;
  const claimed=await run(db,'INSERT OR IGNORE INTO events(id,chat,created,state) VALUES(?,?,?,?)',id,chat,now,'processing');
  if(!claimed.meta.changes)return;
  const text=m.text.trim().replace(/^\//,'').replace(/\s+/g,' ').toUpperCase();
  const count=await first(db,'SELECT count(*) AS n FROM events WHERE chat=? AND created>?',chat,now-60);
  let p=JSON.parse(user.prefs),active=user.active,due=user.due,body=HELP;
  if(text==='STOP'||text==='PAUSE'){active=0;due=null;body='Reports stopped. Send START to start again.';}
  else if(count.n>6){await run(db,"UPDATE events SET state='rate_limited' WHERE id=?",id);return;}
  else if(text==='START'){active=1;due=nextDue(p,now);body=settings(p,active)+' Send STOP at any time.';}
  else if(['STATUS','NOW','1'].includes(text))body=await report(db,chat,now);
  else if(text==='SETTINGS')body=settings(p,active);
  else if(text==='HOMES')body='Your homes:\n'+(await rows(db,'SELECT h.id,h.name FROM homes h JOIN access a ON h.id=a.home WHERE a.chat=?',chat)).map(h=>h.id+': '+h.name).join('\n');
  else if(text==='ALL'){p.home=null;p.room=null;body='All your homes and rooms selected.';}
  else if(text.startsWith('HOME ')){
    const h=text.slice(5).toLowerCase();
    if(await first(db,'SELECT 1 AS ok FROM access WHERE chat=? AND home=?',chat,h)){p.home=h;p.room=null;body='Home selected. Send STATUS.';}else body='Home not available. Send HOMES.';
  }else if(text.startsWith('ROOM ')){
    const target=text.slice(5).toLowerCase();
    const hs=await rows(db,'SELECT s.home,s.payload FROM snapshots s JOIN access a ON s.home=a.home WHERE a.chat=?',chat);
    if(hs.some(h=>(!p.home||p.home===h.home)&&JSON.parse(h.payload).devices.some(d=>d.room.toLowerCase()===target))){p.room=target;body='Room selected. Send STATUS. Send ALL to reset.';}else body='Room not available. Use a room name from your report.';
  }else if(/^(DAILY|EVERY|QUIET) /.test(text)){
    try{const proposed=scheduleCommand(text,p),nd=nextDue(proposed,now);p=proposed;due=active?nd:null;body=settings(p,active)+(active?'':' Send START to allow reports.');}catch(e){body=e.message;}
  }
  // Optimistic revision protects against concurrent commands/scheduler updates.
  const changed=await run(db,'UPDATE users SET prefs=?,active=?,due=?,revision=revision+1 WHERE chat=? AND revision=?',JSON.stringify(p),active,due,chat,user.revision);
  if(!changed.meta.changes){
    // STOP must win even if another update arrived at the same time.
    if(text==='STOP'||text==='PAUSE')await run(db,'UPDATE users SET active=0,due=NULL,revision=revision+1 WHERE chat=?',chat);
    else body='Another setting changed at the same time. Send your command again.';
  }
  if(count.n<=6)await deliver(env,id,chat,body,fetcher);
  else await run(db,"UPDATE events SET state='rate_limited' WHERE id=?",id);
}
export async function tick(env,now=nowSeconds(),fetcher=fetch) {
  // Cap this pilot at five due recipients per minute to fit small free-plan limits.
  const users=await rows(env.DB,'SELECT * FROM users WHERE active=1 AND due<=? ORDER BY due LIMIT 5',now);
  for(const u of users){
    const p=JSON.parse(u.prefs),due=nextDue(p,now);
    const claim=await run(env.DB,'UPDATE users SET due=?,revision=revision+1 WHERE chat=? AND revision=? AND due=? AND active=1',due,u.chat,u.revision,u.due);
    if(!claim.meta.changes||now-u.due>300||isQuiet(now,p))continue;
    const id=`slot:${u.chat}:${u.due}`;
    const job=await run(env.DB,'INSERT OR IGNORE INTO events(id,chat,created,state) VALUES(?,?,?,?)',id,u.chat,now,'processing');
    if(!job.meta.changes)continue;
    const fresh=await first(env.DB,'SELECT active,revision FROM users WHERE chat=?',u.chat);
    if(!fresh.active||fresh.revision!==u.revision+1){await run(env.DB,"UPDATE events SET state='cancelled' WHERE id=?",id);continue;}
    await deliver(env,id,u.chat,await report(env.DB,u.chat,now),fetcher);
  }
  if(Math.floor(now/60)%60===0)await run(env.DB,'DELETE FROM events WHERE created<?',now-7*86400);
}
async function digest(s){return new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));}
async function equal(a,b){const x=await digest(a),y=await digest(b);let n=0;for(let i=0;i<x.length;i++)n|=x[i]^y[i];return n===0;}
export async function route(request,env,now=nowSeconds(),fetcher=fetch){
  const path=new URL(request.url).pathname;
  if(request.method==='GET'&&path==='/healthz')return new Response('ok');
  if(request.method!=='POST'||!['/telegram','/v1/readings'].includes(path))return new Response('Not found',{status:404});
  let home=null;
  if(path==='/telegram'){
    if(!env.TELEGRAM_WEBHOOK_SECRET||!await equal(request.headers.get('X-Telegram-Bot-Api-Secret-Token')||'',env.TELEGRAM_WEBHOOK_SECRET))return new Response('Forbidden',{status:403});
  }else{
    const supplied=(request.headers.get('Authorization')||'').replace(/^Bearer /,'');
    for(const [code,token] of Object.entries(JSON.parse(env.AIRCARE_INGEST_TOKENS_JSON||'{}'))){
      if(typeof token==='string'&&token.length>=32&&await equal(supplied,token)){home=code;break;}
    }
    if(!home||!await first(env.DB,'SELECT 1 AS ok FROM homes WHERE id=?',home))return new Response('Forbidden',{status:403});
  }
  // Read a bounded stream, including requests with no Content-Length.
  const reader=request.body?.getReader();let total=0,chunks=[];
  if(!reader)return new Response('Invalid body',{status:400});
  while(true){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>16384){await reader.cancel();return new Response('Too large',{status:413});}chunks.push(value);}
  const raw=new Uint8Array(total);let at=0;for(const chunk of chunks){raw.set(chunk,at);at+=chunk.length;}
  let data;try{data=JSON.parse(new TextDecoder().decode(raw));}catch{return new Response('Invalid JSON',{status:400});}
  if(!data||typeof data!=='object')return new Response('Invalid body',{status:400});
  if(path==='/telegram')await handleUpdate(env,data,now,fetcher);
  else{
    try{validateSnapshot(data,now);}catch{return new Response('Invalid readings',{status:400});}
    const prior=await first(env.DB,'SELECT payload FROM snapshots WHERE home=?',home);
    if(prior){
      const previous=new Map(JSON.parse(prior.payload).devices.map(d=>[d.id,d]));
      for(const device of data.devices)for(const [key,reading] of Object.entries(device.metrics)){
        const old=previous.get(device.id)?.metrics[key];
        if(old&&old.observed_at>reading.observed_at)device.metrics[key]=old;
      }
    }
    await run(env.DB,'INSERT INTO snapshots(home,payload,received) VALUES(?,?,?) ON CONFLICT(home) DO UPDATE SET payload=excluded.payload,received=excluded.received',home,JSON.stringify({devices:data.devices}),now);
  }
  return new Response('ok');
}
export default {
  async fetch(request,env){return route(request,env);},
  async scheduled(event,env,ctx){ctx.waitUntil(tick(env,Math.floor(event.scheduledTime/1000)));}
};
