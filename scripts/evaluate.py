import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import KnowledgeBase,ROOT
from core.agent import Agent
from core.insights import Insights

kb=KnowledgeBase();agent=Agent(kb)
QUERIES=[('en','What work does the internship include?','product'),('en','What are the eligibility requirements?','qualification'),
 ('en','What stipend do you pay?','policy'),('en','Is this remote or in the office?','faq'),('en','I am a fresher with no experience','objection'),
 ('ph','Mahal po, wala akong pambayad','objection'),('ph','What is a beneficiary or rider?','faq'),
 ('id','Berapa denda kalau terlambat?','policy'),('id','Saya belum bisa bayar','objection'),('id','Apa itu DP dan tenor?','faq'),
 ('en','Who won the football match?',None)]
rows=[]
for market,query,expected in QUERIES:
    t=time.perf_counter();hit=kb.answer(query,market);elapsed=(time.perf_counter()-t)*1000
    actual=hit['topic'] if hit else None
    rows.append({'question':query,'market':market,'expected_topic':expected,'record':hit,'source':hit['source_ref'] if hit else None,
                 'explanation':'Expected topic compared against a hand-labelled query. Unknown questions must return no answer.',
                 'verdict':'correct' if actual==expected else 'incorrect','retrieval_ms':elapsed})
(ROOT/'evidence/retrieval_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
CASES=[('I have a second vehicle to insure','customer',1,'second_vehicle'),('Please pay now to proceed','agent',1,'missing_disclosure'),
 ('Your approval is guaranteed','agent',1,'risky_promise'),('I am frustrated, this is the third time','customer',1,'frustration'),
 ('I cannot pay this month','customer',1,'payment_difficulty'),('Please call me back tomorrow','customer',1,'callback'),
 ('I am ready to proceed','customer',1,'buying_signal'),('I do not have a second vehicle','customer',1,None),
 ('Approval is not guaranteed','agent',1,None),('I am not angry','customer',1,None),('The weather is nice today','customer',1,None),
 ('I have a second vehicle','customer',.2,None),('Hmm','customer',1,None)]
signals=[]
for text,speaker,confidence,expected in CASES:
    out,metrics=Insights().process(text,speaker,confidence)
    predicted=[x['signal'] for x in out]
    signals.append({'text':text,'speaker':speaker,'asr_confidence':confidence,'expected':expected,'predicted':predicted,
                    'passed':(expected in predicted if expected else not predicted),'metrics':metrics})
negative=[x for x in signals if x['expected'] is None]
report={'kind':'text-only labelled rule tests; not an audio accuracy claim','cases':signals,
        'false_positives':sum(bool(x['predicted']) for x in negative),'negative_cases':len(negative),
        'false_negatives':sum(not x['passed'] for x in signals if x['expected'])}
(ROOT/'evidence/nudge_quality.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Retrieval:',sum(r['verdict']=='correct' for r in rows),'/',len(rows))
print('Nudge rule cases:',sum(r['passed'] for r in signals),'/',len(signals))
