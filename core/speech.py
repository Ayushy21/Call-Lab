import asyncio
import io
import math
import os
import threading
import time
import numpy as np
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[1]/'.env')

LANG={'en':'en','ph':'tl','id':'id'}
VOICES={'en':'en-IN-NeerjaNeural','ph':'fil-PH-BlessicaNeural','id':'id-ID-GadisNeural'}
MODEL=None
LOCK=threading.Lock()


def local_transcribe(data,market):
    global MODEL
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    with LOCK:
        if MODEL is None:
            MODEL=WhisperModel(os.getenv('ASR_MODEL','base'),device='cpu',compute_type='int8',
                               cpu_threads=int(os.getenv('ASR_THREADS','4')),num_workers=1)
        audio=decode_audio(io.BytesIO(data),sampling_rate=16000)
        if len(audio)>16000*25: raise ValueError('Audio must be at most 25 seconds per chunk')
        if not len(audio) or float(np.sqrt(np.mean(audio**2)))<.003:
            return {'text':'','confidence':0.,'segments':[],'provider':'local','model':os.getenv('ASR_MODEL','base'),'silence':True}
        # Force the market language separately. Short code-switching clips may still be mistranscribed.
        segments,info=MODEL.transcribe(audio,language=LANG[market],beam_size=3,condition_on_previous_text=False,
                                      vad_filter=True,temperature=0)
        rows=[{'text':s.text.strip(),'start':s.start,'end':s.end,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob} for s in segments]
        useful=[s for s in rows if s['no_speech_prob']<.6]
        conf=sum(math.exp(s['avg_logprob']) for s in useful)/max(len(useful),1)
        return {'text':' '.join(s['text'] for s in useful),'confidence':round(min(conf,1),3),'segments':rows,
                'provider':'local','model':os.getenv('ASR_MODEL','base'),'language':info.language}


async def transcribe(data,market):
    started=time.perf_counter()
    if market not in LANG: raise ValueError('Unknown market')
    if len(data)>4_000_000: raise ValueError('Audio chunk too large')
    if os.getenv('ASR_PROVIDER','local')=='groq':
        import httpx
        key=os.getenv('GROQ_API_KEY')
        if not key: raise RuntimeError('Set GROQ_API_KEY locally, or choose ASR_PROVIDER=local')
        async with httpx.AsyncClient(timeout=30) as client:
            response=await client.post('https://api.groq.com/openai/v1/audio/transcriptions',
                headers={'Authorization':'Bearer '+key},files={'file':('chunk.wav',data,'audio/wav')},
                data={'model':'whisper-large-v3','language':LANG[market],'response_format':'verbose_json','temperature':'0'})
            if response.status_code!=200: raise RuntimeError('Speech provider returned HTTP '+str(response.status_code))
            body=response.json()
            scores=[math.exp(s.get('avg_logprob',-10)) for s in body.get('segments',[]) if s.get('no_speech_prob',0)<.6]
            result={'text':body.get('text',''),'confidence':sum(scores)/max(len(scores),1),'provider':'groq','model':'whisper-large-v3'}
    else:
        result=await asyncio.to_thread(local_transcribe,data,market)
    result['asr_ms']=(time.perf_counter()-started)*1000
    return result


async def synthesize(text,market,voice=None):
    import edge_tts
    chunks=[]
    async for chunk in edge_tts.Communicate(text,voice or VOICES[market]).stream():
        if chunk['type']=='audio':chunks.append(chunk['data'])
    if not chunks: raise RuntimeError('TTS produced no audio')
    return b''.join(chunks)
