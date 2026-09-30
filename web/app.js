const $=id=>document.getElementById(id);
let sid=null, market='en', stream=null, ctx=null, processor=null, active=false, mode='voice', playing=false;
let queue=Promise.resolve(), pending=0, seq=0, rows=[], replayTimer=null, audioSeconds=0, recording=null, stopped=false;
const setStatus=t=>$('status').textContent=t;
async function api(path,body,method='POST'){
 const r=await fetch(path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await r.json(); if(!r.ok)throw Error(data.detail||'Request failed'); return data;
}
function download(data,name,type='application/json'){
 const blob=data instanceof Blob?data:new Blob([typeof data==='string'?data:JSON.stringify(data,null,2)],{type});
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function message(speaker,text,citations=[]){
 const div=document.createElement('div');div.className='message '+speaker;
 const b=document.createElement('b');b.textContent=speaker;div.append(b,document.createTextNode(text));
 if(citations.length){const c=document.createElement('div');c.className='source';c.textContent=citations.map(x=>`${x.record_id} · ${x.source} · v${x.version}`).join(' | ');div.append(c);}
 $('messages').append(div);$('messages').scrollTop=$('messages').scrollHeight;
}
async function speak(text,voiceMarket=market){
 if(!$('speak').checked)return;
 if(!$('audioConsent').checked){setStatus('Allow demo audio processing before using the voice service.');return;}
 playing=true;
 try{const r=await fetch('/api/tts/'+voiceMarket,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
 if(!r.ok)throw Error('TTS unavailable'); const url=URL.createObjectURL(await r.blob());const a=new Audio(url);
 await new Promise((resolve,reject)=>{a.onended=resolve;a.onerror=reject;a.play().catch(reject)});URL.revokeObjectURL(url);
 }catch(e){setStatus('Voice unavailable. The reply is still shown as text.');}finally{playing=false;}
}
async function reply(r){message('agent',r.text,r.citations);$('stage').textContent=r.stage;await speak(r.text,r.voice_market);}
async function start(){
 stop();await queue;market=$('market').value;const r=await api('/api/session',{market});sid=r.session_id;
 $('messages').replaceChildren();$('nudges').replaceChildren();$('liveText').textContent='';rows=[];seq=0;audioSeconds=0;
 await reply(r);setStatus('Session ready.');
}
$('new').onclick=()=>start().catch(e=>setStatus(e.message));
$('turn').onsubmit=async e=>{e.preventDefault();try{if(!sid)await start();const text=$('text').value.trim();if(!text)return;
 $('text').value='';message('customer',text);await reply(await api(`/api/session/${sid}/turn`,{text}));}catch(e){setStatus(e.message)}};
$('search').onsubmit=async e=>{e.preventDefault();try{const r=await api('/api/search',{query:$('query').value,market:$('market').value});$('results').replaceChildren();
 for(const hit of r.results){const div=document.createElement('div');div.className='result';const b=document.createElement('b');b.textContent=hit.title+' · '+hit.score;
 const p=document.createElement('p');p.textContent=hit.content;const small=document.createElement('small');small.textContent=hit.source_ref+' · v'+hit.version;div.append(b,p,small);$('results').append(div);}
 if(!r.results.length)$('results').textContent='No matching approved information.';}catch(e){setStatus(e.message)}};
function showNudges(nudges){for(const n of nudges){const div=document.createElement('div');div.className='nudge';div.dataset.priority=n.priority;div.textContent=`${n.topic.toUpperCase()} · ${n.text}`;
 $('nudges').prepend(div);setTimeout(()=>div.classList.add('expired'),n.expires_after_seconds*1000);}}
$('signal').onsubmit=async e=>{e.preventDefault();try{if(!sid)await start();const r=await api(`/api/session/${sid}/signal`,{text:$('signalText').value,speaker:$('speaker').value,confidence:1});showNudges(r.nudges);setStatus('Text-only test. This does not measure ASR.');}catch(e){setStatus(e.message)}};
function wav(samples,rate){
 const buffer=new ArrayBuffer(44+samples.length*2),v=new DataView(buffer);
 const write=(offset,s)=>[...s].forEach((c,i)=>v.setUint8(offset+i,c.charCodeAt(0)));
 write(0,'RIFF');v.setUint32(4,36+samples.length*2,true);write(8,'WAVE');write(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);
 v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);write(36,'data');v.setUint32(40,samples.length*2,true);
 for(let i=0;i<samples.length;i++)v.setInt16(44+i*2,Math.max(-1,Math.min(1,samples[i]))*32767,true);return new Uint8Array(buffer);
}
function b64(bytes){let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);}
function enqueue(samples,rate,chunkStart){
 if(pending>=2){setStatus('Speech processing is behind. Audio chunk dropped; repeat the missed part.');rows.push({dropped:true});return;}
 const received=performance.now(),sequence=seq++,target=sid,targetMode=mode,speaker=$('speaker').value;pending++;
 queue=queue.then(async()=>{
 const send=performance.now();const r=await api(`/api/session/${target}/audio`,{audio_base64:b64(wav(samples,rate)),speaker,mode:targetMode,sequence});
 const display=performance.now();const row={...r.metrics,sequence,chunk_ms:samples.length/rate*1000,queue_ms:send-received,delivery_and_http_ms:Math.max(0,display-send-r.metrics.server_ms),receive_to_display_ms:display-received,chunk_start_to_display_ms:display-chunkStart,transcript:r.transcript,nudges:r.nudges};rows.push(row);
 $('asr').textContent=(r.metrics.asr_ms/1000).toFixed(2)+'s';$('total').textContent=(row.receive_to_display_ms/1000).toFixed(2)+'s';
 if(r.transcript){$('liveText').textContent+=` ${speaker}: ${r.transcript}`;if(targetMode==='voice')message('customer',r.transcript);}
 showNudges(r.nudges);if(r.reply)await reply(r.reply);setStatus(`Chunk ${sequence+1} processed · ${r.asr.provider}/${r.asr.model}`);
 }).catch(e=>setStatus(e.message)).finally(()=>pending--);
}
async function mic(which){
 if(!$('audioConsent').checked){setStatus('Please allow demo audio processing first.');return;}
 if(!sid)await start();stop();mode=which;stopped=false;stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});ctx=new AudioContext();
 const input=ctx.createMediaStreamSource(stream);processor=ctx.createScriptProcessor(4096,1,1);input.connect(processor);processor.connect(ctx.destination);
 let blocks=[],length=0,first=performance.now();active=true;
 processor.onaudioprocess=e=>{if(!active||playing){blocks=[];length=0;first=performance.now();return;}const x=new Float32Array(e.inputBuffer.getChannelData(0));blocks.push(x);length+=x.length;
 if(length>=ctx.sampleRate*4){const all=new Float32Array(length);let at=0;blocks.forEach(b=>{all.set(b,at);at+=b.length});audioSeconds+=length/ctx.sampleRate;$('progress').textContent=audioSeconds.toFixed(0)+'s';enqueue(all,ctx.sampleRate,first);blocks=[];length=0;first=performance.now();}};
 setStatus(which==='voice'?'Microphone active. Speak after the agent finishes.':'Monitoring live audio. Choose the correct speaker channel.');
}
function stop(){active=false;stopped=true;if(replayTimer){clearTimeout(replayTimer);replayTimer=null;}if(processor){processor.disconnect();processor=null;}if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}if(ctx){ctx.close();ctx=null;}}
$('mic').onclick=()=>mic('voice').catch(e=>setStatus(e.message));$('monitor').onclick=()=>mic('insights').catch(e=>setStatus(e.message));$('stop').onclick=()=>{stop();setStatus('Audio stopped. Any received chunk will finish processing.');};
async function replay(file){
 if(!$('audioConsent').checked){setStatus('Please allow demo audio processing first.');return;}
 if(!sid)await start();stop();stopped=false;mode='insights';const decoder=new AudioContext(),buffer=await decoder.decodeAudioData(await file.arrayBuffer());await decoder.close();
 const data=buffer.getChannelData(0),rate=buffer.sampleRate;let offset=0;const began=performance.now();audioSeconds=0;
 function schedule(){if(stopped)return;const end=Math.min(offset+rate*4,data.length),chunk=data.slice(offset,end),startAt=began+offset/rate*1000,readyAt=began+end/rate*1000;
 replayTimer=setTimeout(()=>{audioSeconds=end/rate;$('progress').textContent=audioSeconds.toFixed(1)+'s';enqueue(chunk,rate,startAt);offset=end;if(offset<data.length)schedule();else{active=false;setStatus('Replay audio ended. Waiting for last chunk.');}},Math.max(0,readyAt-performance.now()));}
 active=true;setStatus('Replaying at real-time speed. Audio is sent only after each chunk has elapsed.');schedule();
}
$('replay').onchange=e=>{if(e.target.files[0])replay(e.target.files[0]).catch(e=>setStatus(e.message));};
window.replayEvidence=async name=>{const r=await fetch('/api/evidence/'+name);await replay(new File([await r.blob()],name));};
window.getLatencyRows=()=>rows;
$('export').onclick=async()=>{if(sid)download(await api(`/api/session/${sid}/export`,undefined,'GET'),'call-transcript.json');};
$('metrics').onclick=()=>download({note:'Receive means complete chunk available; chunk_start includes buffering. LLM unused.',rows},'latency.json');
fetch('/api/evidence').then(r=>r.json()).then(names=>{for(const name of names){const a=document.createElement('a');a.href='/api/evidence/'+encodeURIComponent(name);a.textContent=name;a.target='_blank';$('evidence').append(a);}}).catch(()=>{});
