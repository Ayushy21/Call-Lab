"""Synthetic Javanese-voice stress test, not a native regional-accent certification."""
import asyncio,io,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT,KnowledgeBase
from core.agent import Agent
from core.speech import synthesize,transcribe
from scripts.record_calls import wav_bytes,wer
from faster_whisper.audio import decode_audio

async def main():
    agent=Agent(KnowledgeBase());s,r=agent.start('id');agent.turn(s,'iya');rows=[];parts=[]
    for text in ['Iya, monggo. Saya belum bisa bayar cicilan sekarang.','Mas, angsurannya jatuh tempo kapan?','Saya mau bicara dengan petugas.']:
        b=await synthesize(text,'id','jv-ID-DimasNeural');asr=await transcribe(b,'id')
        reply=agent.turn(s,asr['text']) if asr['text'] and asr['confidence']>=.45 else agent.reply(s,'fallback')
        rows.append({'reference':text,'asr':asr,'wer':wer(text,asr['text']),'reply':reply})
        parts.extend([decode_audio(io.BytesIO(b)),np.zeros(8000,dtype=np.float32),decode_audio(io.BytesIO(await synthesize(reply['text'],'id'))),np.zeros(8000,dtype=np.float32)])
    result={'kind':'Synthetic regional-language voice stress test','customer_voice':'jv-ID-DimasNeural','asr_language':'id',
            'warning':'This is a Javanese TTS voice reading mixed Indonesian/Javanese text. It is only an accent proxy. No native speaker validated it. It does not establish performance on real regional Indonesian accents.', 'rows':rows}
    (ROOT/'evidence/regional_proxy.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'evidence/regional_proxy.wav').write_bytes(wav_bytes(np.concatenate(parts)))
    print('Regional synthetic probe saved.')

if __name__=='__main__':asyncio.run(main())
