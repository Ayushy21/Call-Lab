import re
import uuid
from dataclasses import dataclass, field
from .kb import redact


@dataclass
class Session:
    market: str
    id: str = field(default_factory=lambda:uuid.uuid4().hex)
    stage: str = 'consent'
    slots: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    consent: bool = False


class Agent:
    def __init__(self,kb): self.kb=kb

    def reply(self,s,topic,extra=''):
        record=self.kb.topic(s.market,topic)
        if record is None: raise ValueError('Missing approved topic: '+topic)
        english=s.market=='ph' and s.slots.get('reply_language')=='en'
        message=(record.get('english_content',record['content']) if english else record['content'])+extra
        result={'text':message,'voice_market':'en' if english else s.market,'citations':[{'record_id':record['record_id'],'source':record.get('english_source',record['source_ref']) if english else record['source_ref'],'version':record['version']}],
                'stage':s.stage,'slots':dict(s.slots),'actions':list(s.actions),'session_id':s.id}
        s.history.append({'speaker':'agent',**result})
        return result

    def start(self,market):
        if market not in ('en','ph','id'): raise ValueError('Unknown market')
        s=Session(market)
        return s,self.reply(s,'intro')

    def turn(self,s,text):
        t=text.lower().strip()
        s.history.append({'speaker':'customer','text':redact(text)})
        if s.stage=='ended': return self.reply(s,'goodbye')
        if s.market=='ph' and re.search(r'speak english|in english|english please',t):
            s.slots['reply_language']='en'
            return self.reply(s,'consent' if s.stage=='consent' else 'product')
        if s.market=='ph' and re.search(r'tagalog please|speak tagalog|filipino please',t):
            s.slots['reply_language']='tl'
            return self.reply(s,'consent' if s.stage=='consent' else 'product')
        if re.search(r'\b(stop|unsubscribe|do not call|huwag|berhenti|jangan telepon)\b',t):
            s.stage='ended'; s.actions.append({'type':'do_not_contact','mock':True})
            return self.reply(s,'goodbye')
        if re.search(r'\b(human|person|advisor|tao|agent|ahente|petugas|manusia|operator)\b',t):
            s.actions.append({'type':'human_escalation','mock':True,'status':'requested_not_connected'})
            return self.reply(s,'human')
        if re.search(r'ignore .*instructions|system prompt|guarantee approval|reveal .*secret',t):
            return self.reply(s,'fallback')
        if s.stage=='consent':
            if re.search(r'\b(no|hindi|ayaw|tidak|nggak|gak)\b',t):
                s.stage='ended'; return self.reply(s,'goodbye')
            if not re.search(r'\b(yes|okay|ok|agree|sige|oo|opo|ya|iya|boleh|monggo)\b',t):
                return self.reply(s,'consent')
            s.consent=True
            s.stage='python' if s.market=='en' else 'discussion'
            return self.reply(s,'ask_python' if s.market=='en' else 'product')
        if re.search(r'\b(callback|call back|later|busy|mamaya|tawag.*bukas|nanti|sibuk|besok)\b',t):
            s.actions.append({'type':'callback_request','mock':True,'status':'time_requires_human_confirmation'})
            return self.reply(s,'callback')
        if s.market=='en':
            # Check contradictions even after qualification. Never silently overwrite a slot.
            hours=re.search(r'\b(\d{1,3})\s*(?:hours?|hrs?)\b',t)
            if hours:
                value=int(hours.group(1))
                if value>80: return self.reply(s,'invalid_hours')
                if 'hours' in s.slots and s.slots['hours']!=value:
                    s.slots['pending_hours']=value; s.stage='confirm_hours'
                    return self.reply(s,'conflict')
                s.slots['hours']=value
            if s.stage=='confirm_hours':
                if re.search(r'\b(yes|correct|confirm)\b',t):
                    s.slots['hours']=s.slots.pop('pending_hours'); s.stage='hours'
                elif re.search(r'\b(no|keep|original)\b',t):
                    s.slots.pop('pending_hours',None); s.stage='hours'
                else: return self.reply(s,'conflict')
            if s.stage=='python':
                if re.search(r'^(yes|yeah|yep)\b|\b(?:built|use|used|know|worked|have)\b.*\bpython\b',t) and not re.search(r'\b(no|not|never)\b',t):
                    s.slots['python']=True; s.stage='hours'
                    if 'hours' not in s.slots: return self.reply(s,'ask_hours')
                elif re.search(r'^(no|not yet|never)\b|(?:do not|don.t|never)\s+(?:know|use|used|built|worked).*python',t):
                    s.slots['python']=False; s.stage='hours'
                    if 'hours' not in s.slots: return self.reply(s,'ask_hours')
            if s.stage=='hours' and 'hours' in s.slots:
                rules=self.kb.topic('en','qualification')['rules']
                s.stage='complete'
                qualified=s.slots.get('python') is True and s.slots['hours']>=rules['minimum_hours']
                s.actions=[a for a in s.actions if a['type']!='screening_summary']
                s.actions.append({'type':'screening_summary','mock':True,'preliminary_match':qualified,
                                  'hours':s.slots['hours'],'python':s.slots.get('python'),'final_decision':'human_reviewer'})
                return self.reply(s,'qualified' if qualified else 'not_qualified')
        answer=self.kb.answer(t,s.market)
        if answer:
            return self.reply(s,answer['topic'])
        if s.stage=='hours' and re.search(r'not sure|maybe|unsure',t): return self.reply(s,'incomplete')
        return self.reply(s,'fallback')
