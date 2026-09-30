"""Small, traceable lexical index. No generated policy text."""
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def redact(text):
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', text)
    text = re.sub(r'(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)', '[PHONE_OR_ID]', text)
    text = re.sub(r'(?i)\b(name|customer name|nama)\s*:\s*[^;\n]+', r'\1: [NAME]', text)
    return text


def tokens(text):
    stop = {'the','a','an','is','are','do','does','i','my','can','what','how','to','for','of','in','it','you','me','and','please',
            'apa','itu','dan','saya','yang','ini','po','ang','ano','ko','sa','ba','akong','kung'}
    return [t for t in re.findall(r'\w+', text.lower()) if t not in stop]


def clean(text):
    lines, seen = [], set()
    for line in text.splitlines():
        line = re.sub(r'\s+', ' ', line).strip()
        if not line or re.match(r'^(Navigation|Copyright|Cookie banner|Page \d+)', line, re.I):
            continue
        if line.lower() not in seen:
            lines.append(line)
            seen.add(line.lower())
    return '\n'.join(lines)


def extract(path):
    if path.suffix == '.pdf':
        import pymupdf
        with pymupdf.open(path) as doc:
            return '\n'.join(p.get_text() for p in doc)
    if path.suffix == '.html':
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        for tag in soup.select('nav,header,footer,script,style,aside'):
            tag.decompose()
        return soup.get_text('\n', strip=True)
    if path.suffix == '.csv':
        with path.open(encoding='utf-8', newline='') as f:
            return '\n'.join(' | '.join(row.values()) for row in csv.DictReader(f))
    return path.read_text(encoding='utf-8')


def build():
    manifest = json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    records, issues, seen = [], [], []
    for item in manifest:
        path = ROOT/'data'/item['file']
        try:
            raw = extract(path)
            if len(raw.strip()) < 15:
                raise ValueError('No usable text. Scanned PDFs need OCR and review.')
            date.fromisoformat(item['effective_date'])
            content = clean(raw)
            safe = redact(content)
            if item.get('approved') is not True:
                issues.append({'source': item['file'], 'reason': 'Unapproved or conflicting source quarantined'})
                continue
            duplicate = next((r for r in seen if r['market']==item['market'] and SequenceMatcher(None,r['content'].lower(),safe.lower()).ratio()>.94), None)
            if duplicate:
                duplicate['also_in'].append(item['file'])
                issues.append({'source':item['file'],'reason':'Duplicate of '+duplicate['record_id']})
                continue
            # Keep short policy sections intact. Long sources split at paragraph/sentence boundaries.
            parts, current = [], ''
            for sentence in re.split(r'(?<=[.!?])\s+|\n\n', safe):
                if len(current.split())+len(sentence.split())>160 and current:
                    parts.append(current.strip()); current=''
                current += sentence+' '
            if current.strip(): parts.append(current.strip())
            for n, part in enumerate(parts):
                record = {**item, 'record_id':item['id']+f'-{n+1}', 'content':part.strip(),
                          'source_ref':item['file']+f'#chunk-{n+1}', 'sha256':hashlib.sha256(raw.encode()).hexdigest(),
                          'pii_redacted':safe!=content, 'also_in':[], 'chunk':n+1}
                if item.get('english_source'):
                    record['english_content']=redact(clean(extract(ROOT/'data'/item['english_source'])))
                records.append(record); seen.append(record)
        except Exception as exc:
            issues.append({'source':item['file'],'reason':str(exc)})
    (ROOT/'data/kb.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'evidence').mkdir(exist_ok=True)
    (ROOT/'evidence/ingestion.json').write_text(json.dumps({'records':len(records),'issues':issues},indent=2),encoding='utf-8')
    return records


class KnowledgeBase:
    def __init__(self):
        self.records = json.loads((ROOT/'data/kb.json').read_text(encoding='utf-8'))

    def topic(self, market, topic):
        return next((r for r in self.records if r['market']==market and r['topic']==topic), None)

    def search(self, query, market='en', limit=3):
        docs = [r for r in self.records if r['market']==market and r['category']!='internal']
        q = tokens(query)
        if not q: return []
        corpus = [tokens(r['title']+' '+r['keywords']+' '+r['content']) for r in docs]
        avg = sum(map(len,corpus))/max(len(corpus),1)
        results=[]
        for record, words in zip(docs,corpus):
            tf=Counter(words); score=0.; matched=set()
            for term in set(q):
                if not tf[term]: continue
                matched.add(term)
                df=sum(term in ws for ws in corpus)
                idf=math.log(1+(len(docs)-df+.5)/(df+.5))
                score+=idf*tf[term]*2.2/(tf[term]+1.2*(.25+.75*len(words)/max(avg,1)))
            if score>0:
                score += 2 * sum(bool(re.search(r'(?<!\w)'+re.escape(k.strip())+r'(?!\w)',query.lower())) for k in record['keywords'].split('|'))
                results.append({**record,'score':round(score,4),'matched':sorted(matched),
                                'coverage':len(matched)/len(set(q))})
        return sorted(results,key=lambda r:r['score'],reverse=True)[:limit]

    def answer(self, query, market):
        hits=self.search(query,market)
        if not hits or hits[0]['score']<1.0 or hits[0]['coverage']<.24:
            return None
        # A short curated lexicon must agree with the candidate topic.
        # Exact source text is returned, not an unsupported LLM completion.
        first=hits[0]
        keyword_phrases=first['keywords'].lower().split('|')
        if not any(re.search(r'(?<!\w)'+re.escape(k.strip())+r'(?!\w)',query.lower()) for k in keyword_phrases):
            return None
        return first
