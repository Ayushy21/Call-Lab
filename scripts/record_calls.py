"""Run synthesized customer speech through real ASR and the agent, saving honest results."""
import asyncio,io,json,re,sys,time,wave
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT,KnowledgeBase
from core.agent import Agent
from core.speech import synthesize,transcribe
from faster_whisper.audio import decode_audio

CALLS=[
 ('q1_cooperative','en',['Yes, okay.','Yes, I built a Python project.','I can spend twenty five hours each week.'],['ask_python','ask_hours','qualified']),
 ('q1_objection','en',['Yes, okay.','I am a beginner with no experience.','What is the weather on Mars?','I want to speak to a human.'],['ask_python','objection','fallback','human']),
 ('q1_conflict','en',['Yes, okay.','Yes, I use Python.','I am not sure about my hours.','I can work thirty hours.','Actually, I can work ten hours.','Yes, that is correct.'],['ask_python','ask_hours','incomplete','qualified','conflict','not_qualified']),
 ('q3_ph_cooperative','ph',['Opo, sige po.','Ano po ang beneficiary at rider sa policy?','Medyo mahal po, wala akong pambayad ngayon.','Puwede po bang makausap ang tao?'],['product','faq','objection','human']),
 ('q3_ph_mixed','ph',['Yes, okay po.','What happens sa coverage kung late ang premium?','Busy ako, tawag na lang mamaya.','Ano ang weather bukas?'],['product','policy','callback','fallback']),
 ('q3_id_cooperative','id',['Iya, boleh lanjut.','Apa itu DP dan tenor?','Berapa denda kalau terlambat?','Saya mau bicara dengan petugas.'],['product','faq','policy','human']),
 ('q3_id_colloquial','id',['Iya, monggo.','Saya belum bisa bayar, cicilannya berat.','Mas, ora iso bayar sekarang.','Telepon lagi besok saja.'],['product','objection','objection','callback']),
]

def wav_bytes(samples,rate=16000):
    f=io.BytesIO()
    with wave.open(f,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
    return f.getvalue()

def wer(reference,hypothesis):
    a=re.findall(r'\w+',reference.lower());b=re.findall(r'\w+',hypothesis.lower())
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=row
    return round(prev[-1]/max(len(a),1),3)

async def main():
    agent=Agent(KnowledgeBase()); summary=[]
    cache=ROOT/'runtime/tts';cache.mkdir(parents=True,exist_ok=True)
    async def audio(text,market,customer=False):
        import hashlib
        voice={'en':'en-IN-PrabhatNeural','ph':'fil-PH-AngeloNeural','id':'id-ID-ArdiNeural'}[market] if customer else None
        key=hashlib.sha256((text+market+str(voice)).encode()).hexdigest()+'.mp3';path=cache/key
        if not path.exists():
            for attempt in range(3):
                try:path.write_bytes(await synthesize(text,market,voice));break
                except Exception:
                    if attempt==2:raise
                    await asyncio.sleep(1)
        return path.read_bytes()
    for name,market,inputs,expected in CALLS:
        s,intro=agent.start(market);parts=[];rows=[]
        b=await audio(intro['text'],market);parts+=[decode_audio(io.BytesIO(b)),np.zeros(8000,dtype=np.float32)]
        rows.append({'speaker':'agent','text':intro['text'],'citations':intro['citations']})
        for sentence,topic in zip(inputs,expected):
            b=await audio(sentence,market,True);parts+=[decode_audio(io.BytesIO(b)),np.zeros(4800,dtype=np.float32)]
            result=await transcribe(b,market)
            response=agent.turn(s,result['text']) if result['text'] and result['confidence']>=.45 else agent.reply(s,'fallback')
            actual=response['citations'][0]['record_id']
            rows.append({'speaker':'customer','reference':sentence,'asr':result,'word_error_rate':wer(sentence,result['text']),
                         'expected_topic':topic,'actual_record':actual,'passed':actual==market+'_'+topic+'-1'})
            rows.append({'speaker':'agent','text':response['text'],'citations':response['citations'],'stage':response['stage']})
            b=await audio(response['text'],market);parts+=[decode_audio(io.BytesIO(b)),np.zeros(8000,dtype=np.float32)]
        out={'kind':'synthetic TTS customer -> real local ASR -> real agent -> TTS reply; not a human call',
             'market':market,'regional_accent':'Not tested; Indonesian colloquial words use a standard synthetic voice.' if market=='id' else None,
             'rows':rows,'actions':s.actions}
        (ROOT/f'evidence/{name}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/f'evidence/{name}.wav').write_bytes(wav_bytes(np.concatenate(parts)))
        customer=[r for r in rows if r['speaker']=='customer']
        summary.append({'call':name,'market':market,'turns':len(customer),'passed':sum(r['passed'] for r in customer),
                        'mean_wer':sum(r['word_error_rate'] for r in customer)/len(customer),
                        'asr_ms':[r['asr']['asr_ms'] for r in customer]})
        print(name,summary[-1]['passed'],'/',len(customer),flush=True)
        (ROOT/'evidence/voice_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Q4 source: synthetic audio only; no text is sent to the live ASR endpoint.
    scenarios=[('q4_customer','en','I have a second vehicle to insure. I would like to know the next step. I am frustrated. This is the third time I have called. Please call me back tomorrow.'),
               ('q4_agent','en','Your approval is guaranteed. Please pay now to proceed. We can finish the application today.'),
               ('q4_negative','en','The weather is nice today. I do not have a second vehicle. I am not angry. Thank you for explaining the process.')]
    for name,market,sentence in scenarios:
        b=await audio(sentence,market,True)
        samples=decode_audio(io.BytesIO(b))
        (ROOT/f'evidence/{name}.wav').write_bytes(wav_bytes(samples))
    # Silence and noise should not generate fabricated useful text.
    rng=np.random.default_rng(42)
    (ROOT/'evidence/q4_noise.wav').write_bytes(wav_bytes(rng.normal(0,.001,16000*8).astype(np.float32)))
    print('Saved all synthetic calls and streaming fixtures.',flush=True)

if __name__=='__main__':asyncio.run(main())
