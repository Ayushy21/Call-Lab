"""Build the plain-English report from measured evidence, plus a readable PDF."""
import json,sys,textwrap,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT

def read(name):return json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8'))

def main():
    voice=read('voice_summary.json');retrieval=read('retrieval_results.json');latency=read('latency_report.json');live=read('live_audio_results.json');quality=read('nudge_quality.json');ingestion=read('ingestion.json')
    suite=ET.parse(ROOT/'evidence/test_results.xml').getroot()
    tests=sum(int(s.attrib.get('tests',0)) for s in suite.findall('testsuite'))
    failures=sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suite.findall('testsuite'))
    calls='\n'.join(f"- {r['call']}: {r['passed']}/{r['turns']} expected responses; mean turn word error rate {r['mean_wer']:.1%}." for r in voice)
    times='\n'.join(f"- {key}: P50 {latency[key]['p50']:.1f} ms; P95 {latency[key]['p95']:.1f} ms; {latency[key]['samples']} chunks." for key in ['asr_ms','signal_ms','llm_ms','delivery_and_http_ms','receive_to_display_ms','chunk_start_to_display_ms'])
    found='\n'.join(f"- {r['file']}: {r['nudges_before_end']} chunks produced an alert before audio ended. Signals: {', '.join(n['signal'] for row in r['rows'] for n in row['nudges']) or 'none'}." for r in live)
    queries='\n'.join(f"- {r['question']} -> {r['record']['record_id'] if r['record'] else 'safe fallback'}; {r['verdict']}." for r in retrieval)
    report=f'''DARWIX AI ENGINEER ASSESSMENT
Ayush Yadav

WHAT I BUILT

I built a local web app called Call Lab. It has a candidate-screening voice flow, a shared knowledge base, two localized finance demo flows, and live call alerts. The code, recordings, transcripts, tests, and setup steps are included.

I was given only the assessment PDF. No scripts, company policies, account data, or platform access were supplied. I therefore used fictional business rules and sample accounts. These are examples for testing, not real financial or employment information.

The speech recognition is real. The customer voices in the saved test calls are synthetic. I did not speak to real customers or claim native-speaker validation. The local web interface is the calling interface. No phone number is connected.

QUESTION 1 - GROUNDED VOICE AGENT

I chose candidate screening. A fictional internship asks whether the caller has built a Python project and how many hours they can spend each week. The approved demo rule is a Python project and at least 20 hours a week. Passing this check is only a preliminary match. A human makes the final decision.

The flow is: explain the demo, ask permission, ask about Python, ask about hours, then give a preliminary result. If hours are missing, the bot leaves them unconfirmed. If the caller changes an earlier number, the bot asks before replacing it. A stop request ends the flow. A request for a person creates a local mock escalation and clearly says that no person is connected.

FAQs, objections, policy answers, and qualification rules come from the Question 2 knowledge base. The bot returns approved source text and a citation. It does not have a large prompt containing all the answers. If it cannot find a supported answer, it says so. This makes the wording less flexible, but keeps the small demo predictable.

Three English recordings cover a cooperative caller, lack-of-experience objection, missing hours, changed hours, an unrelated question, and a request for a human. They are in evidence/q1_*.wav. Matching JSON files contain the reference speech, actual ASR output, source record, expected response, and result.

The optional business action is a mock screening summary, callback request, or escalation. These are kept in the local session and can be downloaded. No message or job application is sent to an outside service.

QUESTION 2 - KNOWLEDGE BASE

The input set has local text, saved HTML, a CSV table, and generated PDFs. It also has a duplicate page, an unapproved conflicting claim, a fake form with sample PII, a broken PDF, and a missing file. This lets the tests show what happens when input is messy.

For a website, I would first save an allowed page with its URL and retrieval time, then extract the main content. In this implementation I parse saved HTML. Navigation, headers, footers, scripts, and sidebars are removed. PDFs use text extraction. Scanned PDFs are flagged for OCR and review; OCR is not implemented. Tables keep their row values. Repeated lines and near-duplicate sections are removed. Failures are logged instead of silently producing empty records.

The manifest gives each section a stable topic, market, language, category, source file, owner, version, and ISO date. Dates are checked before indexing. English and local-language finance terms are listed as search keywords. Conflicting content in the sample is explicitly unapproved and excluded. The system does not automatically resolve every possible contradiction; a reviewer must approve policy changes.

Basic PII masking removes labelled names, email addresses, and phone or ID-like numbers from indexed content and saved conversation text. This is a small regex-based filter. It cannot find every unlabelled name, address, or sensitive medical detail. Only fictional data should be used in this prototype. Real use needs stronger PII detection and access controls.

The schema includes record_id, title, content, category, topic, market, language, source_ref, version, effective_date, owner, sha256, pii_redacted, and also_in. The hash identifies the source bytes. The also_in field keeps duplicate-source links. Qualification rules are stored as structured fields on the approved record.

Example: en_qualification-1, category qualification, market en, version 1.0, with a source link and minimum_hours set to 20. The sample records are in data/kb.json.

I keep short sections whole. Longer text is split at sentence boundaries around 160 words. I use BM25-style word scoring with a keyword boost, market filtering, and a minimum relevance check. There are no embeddings in this version. For this small approved set, lexical search is easy to inspect and test. For a larger set I would add multilingual embeddings, combine lexical and vector results, and test a reranker on labelled questions before using it.

The index currently contains {ingestion['records']} approved records. Retrieval passed {sum(r['verdict']=='correct' for r in retrieval)}/{len(retrieval)} labelled queries. These queries were used during development, so they are not an independent benchmark. Each full result includes the retrieved text, source reference, expected topic, reason, timing, and verdict in evidence/retrieval_results.json.

{queries}

QUESTION 3 - PHILIPPINES AND INDONESIA

The Philippines flow is a fictional life-insurance premium reminder. The default voice is fil-PH-BlessicaNeural. Recognition uses local faster-whisper base with the language set to tl. It accepts Filipino and Taglish. A caller can say English please to select English replies and English ASR, or Tagalog please to switch back. English support is tested in the text flow; pure-English speech in the Philippines flow has not been separately benchmarked.

Three localization choices for the Philippines:
1. The reminder uses polite po and asks permission before continuing. A budget objection gets an understanding reply instead of pressure to pay.
2. Premium, policy, beneficiary, rider, lapse, coverage, and bank referral stay in familiar insurance wording. The bot does not force an awkward literal translation.
3. The sample amount is spoken in pesos and the date is spoken out. Callback times use Philippine time. A late payment does not cause the bot to invent a lapse date or grace period.

The Indonesia flow is a fictional installment reminder. The default voice is id-ID-GadisNeural. Recognition uses the same local model but with language id. Replies stay in Indonesian. Colloquial words are accepted where the recognizer and keyword set support them.

Three localization choices for Indonesia:
1. The flow uses cicilan or angsuran for the payment, tenor for its term, DP for the down payment, denda for penalties, and jatuh tempo for the due date.
2. The sample amount is spoken as five hundred thousand rupiah. A callback must confirm WIB, WITA, or WIT rather than assume one timezone for the whole country.
3. A caller saying belum bisa bayar or a colloquial equivalent gets an offer of human help. The bot does not threaten the caller or promise a fee waiver, new tenor, or approval.

Each market has two synthetic call recordings with actual ASR transcripts. The Philippines tests include code-switching, an objection, a policy question, callback, and human help. Indonesia includes formal and colloquial speech, a fee question, finance terms, and human help.

I also ran a separate stress test using jv-ID-DimasNeural, a Javanese TTS voice, reading mixed Indonesian and Javanese wording. This is only a synthetic regional-language proxy. It is not proof of recognition quality for a real Javanese-accented Indonesian speaker. The results and audio are in evidence/regional_proxy.*. It misheard local words and sometimes used fallback. A real speaker from outside Jakarta still needs to test the system.

Measured call results:
{calls}

Word error rate compares the recognized words with the synthetic script. The reported value is the mean of turn-level scores, not a population accuracy estimate. Numbers, spelling, and abbreviations can change that score even when meaning is preserved. Response counts compare the actual source selected with the expected topic.

Known gaps: a Filipino affordability sentence and an Indonesian regional phrase were misheard in the synthetic tests. The bot used fallback. The regional proxy also missed a human-help phrase. This is not good enough for a real launch. I would test a stronger speech model and a held-out set of native recordings, including phone audio, background noise, and code-switching. Local speakers and the business must review the scripts, consent wording, and policy terms.

QUESTION 4 - LIVE INSIGHTS

The browser can use a microphone or replay audio at normal speed. The replay sends four-second chunks only after that much audio time has elapsed. The backend transcribes each chunk and runs the alert rules immediately. The whole recording is not uploaded and analyzed after the call.

The agent/customer label comes from the selected audio channel. There is no automatic diarization. On a real call platform, separate media channels would provide this label. The prototype does not infer speaker identity from one mixed recording.

The rules detect a second-vehicle opportunity, a promise of guaranteed approval, a missing demo disclosure before asking for payment, frustration, payment difficulty, a callback request, and buying intent. Each alert suggests one short next step. For example, a second vehicle leads to asking about a separate quote, not inventing a multi-vehicle discount.

Controls include an ASR score cutoff of 0.50, negation checks, a short per-speaker context, a 30-second per-signal cooldown, priorities, topic labels, at most two alerts per chunk, and a 20-second display expiry. The ASR score is a heuristic, not a calibrated probability. I lowered the original cutoff after it missed clear synthetic phrases. That choice needs an independent human-audio evaluation.

Testing also found a false opportunity alert when a negative sentence was split between chunks. I changed the rule to require an ownership statement and added positive and negative chunk-boundary regression tests.

There is no LLM in the alert path. Its LLM time is therefore zero, not an omitted measurement. Timing starts when a complete audio chunk is available and continues through ASR, signal detection, response delivery, and client display. I also report time from the start of the chunk, which includes the four-second capture buffer.

Measured CLI replay latency:
{times}

These are local measurements on {latency['asr_ms']['samples']} chunks, not a production SLA. ASR time includes local model queueing and cold start if present. Delivery is HTTP plus client overhead. Browser timing is saved separately in evidence/browser_latency.json. It measures client receipt and DOM update scheduling, not exact display paint time.

Observed live signals:
{found}

The text-only quality set has {len(quality['cases'])} cases. It recorded {quality['false_positives']} false positives on {quality['negative_cases']} negative cases and {quality['false_negatives']} missed expected signals. The audio false-positive checks are listed in latency_report.json. They use one negative conversation and low-level synthetic noise. They do not establish performance on difficult real-world noise.

AT TEN TIMES THE LOAD

The current local speech model has one lock, so calls will queue. Session data is in memory and will be lost on restart. I would separate audio processing from the web server, use bounded queues, move session state into a shared store, and add worker capacity based on load tests. I would measure ASR delay and dropped chunks per call, not only total request counts.

For noisy audio, I would test better ASR, overlapping chunks, speech detection, and longer context. I would ask the caller to confirm dates, amounts, and unclear answers. Silence must not become a confident answer. A genuine regional-accent test and native-language review remain necessary.

WHAT IS INCLUDED AND WHAT IS LEFT

Included: working local source code, README, environment template, source fixtures, shared knowledge base, {tests} automated tests with {failures} failures, retrieval evidence, seven synthetic calls, transcripts, a regional proxy, live audio results, latency report, screenshot, and video walkthrough materials.

No API secrets or real customer data are included. The default setup needs no paid API account. First-time model download and online TTS need internet. The optional Groq path is implemented but not account-tested.

The prototype still needs approved business sources, real native-speaker calls, a stronger speech-quality check, authentication, encrypted storage where needed, tenant isolation, proper consent and retention rules, and a real human handoff before production use. The recordings are synthetic tests. Do not describe them as real customer recordings.

The video uses an automated screen recording and clearly labelled synthetic narration where included. A candidate should run the app, understand the code, and record a personal walkthrough before claiming they can explain every choice.

TECHNICAL REFERENCES

faster-whisper: https://github.com/SYSTRAN/faster-whisper
Edge TTS: https://github.com/rany2/edge-tts
Optional Groq speech API: https://console.groq.com/docs/speech-to-text

All financial and employment examples in this submission are fictional. These references explain tools, not business policy.
'''
    (ROOT/'ANSWERS.txt').write_text(report,encoding='utf-8')
    import pymupdf
    doc=pymupdf.open();font=pymupdf.Font('helv')
    page=None;y=0
    def new_page():
        nonlocal page,y
        page=doc.new_page(width=595,height=842)
        page.insert_text((48,815),f'Ayush Yadav | Darwix assessment | {len(doc)}',fontsize=8,color=(.4,.4,.4))
        y=48
    new_page()
    for paragraph in report.splitlines():
        if not paragraph.strip():y+=8;continue
        heading=paragraph.isupper() and len(paragraph)<70
        size=13 if heading else 10
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if font.text_length(candidate,fontsize=size)>499 and line:
                if y>780:new_page()
                page.insert_text((48,y),line,fontname='helv',fontsize=size);y+=15 if heading else 13
                line=word
            else:line=candidate
        if line:
            if y>780:new_page()
            page.insert_text((48,y),line,fontname='helv',fontsize=size);y+=17 if heading else 13
    doc.save(ROOT/'ANSWERS.pdf');print('Wrote plain-text report and',len(doc),'page PDF.')

if __name__=='__main__':main()
