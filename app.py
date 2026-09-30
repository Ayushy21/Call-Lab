import asyncio
import base64
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from core.kb import KnowledgeBase, ROOT, redact
from core.agent import Agent
from core.insights import Insights
from core.speech import transcribe, synthesize

load_dotenv(ROOT/'.env')
kb=KnowledgeBase(); agent=Agent(kb)
sessions={}; insights={}; touched={}; locks={}; events={}

def get(sid):
    if sid not in sessions: raise HTTPException(404,'Session not found or expired')
    touched[sid]=time.monotonic()
    return sessions[sid]

def cleanup():
    for sid in list(sessions):
        if time.monotonic()-touched[sid]>3600:
            for mapping in (sessions,insights,touched,locks,events):mapping.pop(sid,None)

app=FastAPI(title='Darwix assessment demo')
app.mount('/static',StaticFiles(directory=ROOT/'web'),name='static')

class Start(BaseModel): market: Literal['en','ph','id']='en'
class Turn(BaseModel): text:str=Field(min_length=1,max_length=2000)
class Query(BaseModel): query:str=Field(min_length=1,max_length=1000); market:Literal['en','ph','id']='en'
class Signal(BaseModel):
    text:str=Field(min_length=1,max_length=2000)
    speaker:Literal['agent','customer']='customer'
    confidence:float=Field(default=1,ge=0,le=1)
class Audio(BaseModel):
    audio_base64:str=Field(max_length=5_400_000)
    speaker:Literal['agent','customer']='customer'
    mode:Literal['voice','insights']='voice'
    sequence:int=Field(default=0,ge=0)

@app.get('/')
def home():return FileResponse(ROOT/'web/index.html')

@app.get('/api/health')
def health():return {'status':'ok','records':len(kb.records),'fictional_data':True}

@app.post('/api/session')
def start(body:Start):
    cleanup()
    if len(sessions)>=100:raise HTTPException(429,'Demo session limit reached')
    s,result=agent.start(body.market)
    sessions[s.id]=s; insights[s.id]=Insights(); touched[s.id]=time.monotonic(); locks[s.id]=asyncio.Lock(); events[s.id]=[]
    return result

@app.post('/api/session/{sid}/turn')
async def turn(sid:str,body:Turn):
    s=get(sid)
    async with locks[sid]:return agent.turn(s,body.text)

@app.post('/api/search')
def search(body:Query):return {'results':kb.search(body.query,body.market)}

@app.post('/api/session/{sid}/signal')
async def signal(sid:str,body:Signal):
    get(sid)
    async with locks[sid]:
        nudges,metrics=insights[sid].process(body.text,body.speaker,body.confidence)
        return {'nudges':nudges,'metrics':metrics,'input_type':'text_only_not_audio_evidence'}

@app.post('/api/session/{sid}/audio')
async def audio(sid:str,body:Audio):
    s=get(sid); received=time.perf_counter()
    async with locks[sid]:
        try:
            data=base64.b64decode(body.audio_base64,validate=True)
            speech_market='en' if s.market=='ph' and s.slots.get('reply_language')=='en' else s.market
            result=await transcribe(data,speech_market)
        except Exception as exc:
            # Do not expose paths, provider payloads, or secrets in HTTP errors.
            raise HTTPException(503,'Speech processing failed. Check local model/network; retry or use text mode.') from exc
        text=result['text']
        nudges,metrics=insights[sid].process(text,body.speaker,result['confidence'])
        response={'transcript':redact(text),'asr':result,'nudges':nudges,'sequence':body.sequence,
                  'metrics':{**metrics,'asr_ms':result['asr_ms'],'server_ms':(time.perf_counter()-received)*1000}}
        if body.mode=='voice' and body.speaker=='customer' and text:
            response['reply']=agent.turn(s,text) if result['confidence']>=.45 else agent.reply(s,'fallback')
        response['asr']['text']=redact(text)
        response['asr'].pop('segments',None)
        # Session memory only. Download is explicit; customer audio is never saved here.
        events[sid].append(response)
        return response

@app.post('/api/tts/{market}')
async def tts(market:Literal['en','ph','id'],body:Turn):
    try: return Response(await synthesize(body.text,market),media_type='audio/mpeg')
    except Exception as exc: raise HTTPException(503,'Voice service unavailable; use displayed text or browser voice.') from exc

@app.get('/api/session/{sid}/export')
def export(sid:str):
    s=get(sid)
    return {'market':s.market,'history':s.history,'actions':s.actions,'audio_events':events[sid],
            'note':'Local demo. No real lead, payment, callback, or escalation was sent.'}

@app.delete('/api/session/{sid}')
def remove(sid:str):
    get(sid)
    for mapping in (sessions,insights,touched,locks,events):mapping.pop(sid,None)
    return {'deleted':True}

@app.get('/api/evidence')
def evidence():
    return [p.name for p in (ROOT/'evidence').iterdir() if p.is_file() and p.suffix in ('.json','.txt','.wav','.webm','.mp4','.png')]

@app.get('/api/evidence/{name}')
def evidence_file(name:str):
    path=(ROOT/'evidence'/name).resolve()
    if path.parent!=(ROOT/'evidence').resolve() or not path.is_file():raise HTTPException(404)
    return FileResponse(path)
