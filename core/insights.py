"""Rule-based live suggestions. Confidence values are heuristics, not probabilities."""
import re
import time
import uuid


class Insights:
    def __init__(self):
        self.last={}; self.disclosed=False; self.history=[]; self.previous={}

    def process(self,text,speaker='customer',confidence=1.,now=None):
        now=time.monotonic() if now is None else now
        t=text.lower(); start=time.perf_counter(); candidates=[]
        if confidence<.50 or len(t.split())<3:
            return [], {'reason':'low_confidence_or_too_short','signal_ms':(time.perf_counter()-start)*1000,'llm_ms':0.,'llm_used':False}
        previous=self.previous.get(speaker)
        self.previous[speaker]=(t,now)
        if previous and now-previous[1]<12:
            t=previous[0][-250:]+' '+t
        if speaker=='agent':
            if re.search(r'not (?:a )?guarantee|not guaranteed|subject to review|bukan jaminan|hindi garantisado',t): self.disclosed=True
            if re.search(r'guaranteed approval|approval is guaranteed|guaranteed returns|pasti disetujui',t) and not re.search(r'not guaranteed|not promise|cannot guarantee|no guaranteed',t):
                candidates.append(('risky_promise','compliance',1,'Do not promise approval or returns. Explain that a human must review the case.',.98))
            if re.search(r'pay now|confirm the purchase|send payment',t) and not self.disclosed:
                candidates.append(('missing_disclosure','compliance',1,'Pause. Give the required demo disclosure before asking for payment.',.95))
        else:
            if re.search(r'\b(?:i|we)\s+(?:(?:also|already)\s+)?(?:have|own|bought|got)\s+(?:a\s+)?(?:second vehicle|another car|second car)\b',t) and not re.search(r'\b(no|not|don.t|never)\b.{0,25}\b(second|another)',t):
                candidates.append(('second_vehicle','opportunity',3,'Ask whether they want a separate quote for the second vehicle. Do not invent a discount.',.90))
            if re.search(r'frustrat|angry|third time|stop repeating|kesal|nakakainis',t) and not re.search(r'not (?:angry|frustrated)',t):
                candidates.append(('frustration','sentiment',2,'Acknowledge the concern. Ask what is still unresolved before continuing.',.88))
            if re.search(r'cannot pay|can.t pay|cannot afford|short of money|belum bisa bayar|wala.*pambayad',t):
                candidates.append(('payment_difficulty','support',2,'Offer a human callback through the approved support path. Do not promise a fee waiver.',.92))
            if re.search(r'call (?:me )?(?:back|tomorrow)|callback|telepon.*besok',t):
                candidates.append(('callback','follow_up',3,'Confirm a callback date, time, and timezone. Ask permission before saving it.',.90))
            if re.search(r'ready to proceed|want to sign up|interested in buying',t):
                candidates.append(('buying_signal','intent',3,'Confirm the next step and required consent. Avoid promising approval.',.88))
        nudges=[]
        for key,topic,priority,message,score in sorted(candidates,key=lambda v:v[2]):
            if now-self.last.get(key,-1e9)<30: continue
            if len(nudges)>=2: break
            self.last[key]=now
            nudges.append({'id':uuid.uuid4().hex,'signal':key,'topic':topic,'priority':priority,'text':message,
                           'confidence':score,'expires_after_seconds':20,'created_monotonic':now})
        self.history.extend(nudges)
        return nudges,{'signal_ms':(time.perf_counter()-start)*1000,'llm_ms':0.,'llm_used':False}
