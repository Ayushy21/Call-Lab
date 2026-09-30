"""Replay actual audio at original speed. Never supply reference text to ASR."""
import asyncio,base64,io,json,sys,time,wave
from pathlib import Path
import httpx
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT

def wave_chunk(data,rate):
    b=io.BytesIO()
    with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(data)
    return b.getvalue()

async def run(name,speaker):
    path=ROOT/'evidence'/name
    with wave.open(str(path),'rb') as w:
        rate=w.getframerate();assert w.getnchannels()==1 and w.getsampwidth()==2
        raw=w.readframes(w.getnframes())
    duration=len(raw)/2/rate;rows=[];tasks=[]
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8765',timeout=120) as client:
        sid=(await client.post('/api/session',json={'market':'en'})).json()['session_id']
        began=time.perf_counter()
        async def send(payload,sequence,chunk_begin,chunk_end):
            received=time.perf_counter();r=await client.post(f'/api/session/{sid}/audio',json={'audio_base64':base64.b64encode(payload).decode(),'speaker':speaker,'mode':'insights','sequence':sequence})
            r.raise_for_status();body=r.json();display=time.perf_counter()
            row={'sequence':sequence,'chunk_start_seconds':chunk_begin,'chunk_end_seconds':chunk_end,
                 'received_seconds':received-began,'display_seconds':display-began,
                 'receive_to_display_ms':(display-received)*1000,'chunk_start_to_display_ms':(display-began-chunk_begin)*1000,
                 'delivery_and_http_ms':max(0,(display-received)*1000-body['metrics']['server_ms']),
                 **body['metrics'],'asr_confidence':body['asr']['confidence'],'transcript':body['transcript'],'nudges':body['nudges'],
                 'nudge_before_audio_end':bool(body['nudges']) and display-began<duration}
            rows.append(row)
            print(name,sequence,body['transcript'],[n['signal'] for n in body['nudges']],flush=True)
        chunk_size=rate*2*4
        for sequence,offset in enumerate(range(0,len(raw),chunk_size)):
            end=min(offset+chunk_size,len(raw));end_seconds=end/(rate*2)
            await asyncio.sleep(max(0,began+end_seconds-time.perf_counter()))
            tasks.append(asyncio.create_task(send(wave_chunk(raw[offset:end],rate),sequence,offset/(rate*2),end_seconds)))
        await asyncio.gather(*tasks)
    rows.sort(key=lambda r:r['sequence'])
    return {'file':name,'speaker':speaker,'audio_duration_seconds':duration,'mode':'real-time paced synthetic audio through actual ASR, no reference-text injection',
            'rows':rows,'nudges_before_end':sum(r['nudge_before_audio_end'] for r in rows)}

async def main():
    reports=[]
    for name,speaker in [('q4_customer.wav','customer'),('q4_agent.wav','agent'),('q4_negative.wav','customer'),('q4_noise.wav','customer')]:
        reports.append(await run(name,speaker))
        (ROOT/'evidence/live_audio_results.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    allrows=[row for r in reports for row in r['rows']]
    metrics={}
    for key in ['asr_ms','signal_ms','llm_ms','delivery_and_http_ms','receive_to_display_ms','chunk_start_to_display_ms']:
        values=[row[key] for row in allrows]
        metrics[key]={'p50':float(np.percentile(values,50)),'p95':float(np.percentile(values,95)),'samples':len(values)}
    metrics['definitions']={'asr_ms':'Includes queueing for the local speech model; includes cold start if present.',
        'receive_to_display_ms':'Complete chunk sent by replay client to response parsed in CLI. Not a browser paint time.',
        'chunk_start_to_display_ms':'Includes four-second capture buffer and any server queueing.',
        'llm_ms':'Zero because rules, not an LLM, produce alerts.'}
    metrics['false_positive_audio_checks']=[{'file':r['file'],'nudges':sum(len(x['nudges']) for x in r['rows'])} for r in reports if 'negative' in r['file'] or 'noise' in r['file']]
    (ROOT/'evidence/latency_report.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2),flush=True)

if __name__=='__main__':asyncio.run(main())
