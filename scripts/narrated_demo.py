"""Record the live UI and add disclosed synthetic narration. No fabricated screenshots."""
import asyncio,io,json,sys,time,subprocess
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT
from core.speech import synthesize
from scripts.record_calls import wav_bytes
from faster_whisper.audio import decode_audio
from playwright.async_api import async_playwright
import imageio_ffmpeg

NARRATION=[
('overview','This is Call Lab, a local assessment prototype. This walkthrough uses synthetic narration. Only the assessment PDF was supplied, so the business rules and accounts are fictional. Speech goes through local Whisper, then the conversation state and shared knowledge base. Answers come from approved records. A separate rule engine shows live call alerts.'),
('screen','The English flow screens a candidate. It asks permission, checks for a Python project, and asks about weekly hours. Changing an earlier number requires confirmation. An unrelated question gets a fallback. A human request creates a local demo action, not a real transfer. The source record is shown below each answer.'),
('kb','The same knowledge base supports the search box and the voice flow. It contains text, HTML, PDF and table sources. Each record has a version, source reference, and category. The index uses lexical scoring and keywords, not embeddings. Duplicate and unapproved sources are excluded. The full retrieval report includes expected topics and actual results.'),
('ph','The Philippines flow uses a Filipino voice and accepts Taglish. It uses pesos, polite wording, and familiar insurance terms. The caller can request English. Unknown policy information stays unknown. The saved calls use synthetic customers and real speech recognition, with errors kept in the transcript.'),
('id','The Indonesian flow uses cicilan, tenor, denda and D P. Callback times need a local time zone. The bot does not promise fee waivers. A Javanese synthetic voice was used for a separate stress test. That is only a proxy. It does not replace a real regional speaker or native language review.'),
('live','This is actual audio replay at normal speed. Each four second chunk goes to speech recognition only after its audio time has elapsed. The customer mentions a second vehicle. The dashboard suggests asking about a separate quote. A later frustration signal asks the agent to acknowledge the concern. Alerts appear while the sample call is still running. The counters show measured speech and total processing time.'),
('compliance','Now the selected channel is the agent. The audio includes a promise of guaranteed approval and a payment request without the demo disclosure. The system raises compliance alerts. It does not take a financial action. Priorities, cooldowns and expiry reduce repeated alerts.'),
('limits','The report separates speech time, rule time, delivery, and total time. It also includes the four second capture buffer. There is no language model in the alert path, so that component is zero. Before real use, this needs approved source material, native speaker tests, authentication, better noisy audio recognition, shared state and more speech workers. This is a working prototype with known gaps, not a production launch.')]

async def main():
    cache=ROOT/'runtime/narration';cache.mkdir(parents=True,exist_ok=True);clips={}
    for key,text in NARRATION:
        path=cache/(key+'.mp3')
        if not path.exists():path.write_bytes(await synthesize(text,'en'))
        clips[key]=decode_audio(io.BytesIO(path.read_bytes()))
    timeline=[];audio_parts=[];sample_position=0
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        context=await browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(ROOT/'runtime/narrated_video'),record_video_size={'width':1440,'height':1000})
        page=await context.new_page();start=time.perf_counter()
        await page.goto('http://127.0.0.1:8765/static/overview.html')
        async def say(key):
            nonlocal sample_position
            offset=int((time.perf_counter()-start)*16000)
            if offset>sample_position:audio_parts.append(np.zeros(offset-sample_position,dtype=np.float32));sample_position=offset
            audio_parts.append(clips[key]);sample_position+=len(clips[key]);timeline.append({'section':key,'start_seconds':offset/16000,'text':dict(NARRATION)[key]})
            await page.wait_for_timeout(len(clips[key])/16+900)
        async def turn(text):
            n=await page.locator('.message').count();await page.fill('#text',text);await page.click('#turn button')
            await page.wait_for_function('(n)=>document.querySelectorAll(".message").length>=n+2',arg=n)
        await say('overview')
        await page.goto('http://127.0.0.1:8765');await page.click('#new');await page.wait_for_selector('.message')
        for text in ['yes','yes, I built a Python project','25 hours','Actually 10 hours','yes','What is the weather on Mars?','human please']:await turn(text)
        await say('screen')
        await page.fill('#query','What are the eligibility requirements?');await page.click('#search button');await page.wait_for_selector('.result');await page.locator('#results').scroll_into_view_if_needed();await say('kb')
        for key,consent,question in [('ph','opo','Mahal po, wala akong pambayad'),('id','iya','Berapa denda kalau terlambat?')]:
            await page.select_option('#market',key);await page.click('#new');await page.wait_for_timeout(500);await turn(consent);await turn(question);await page.locator('#messages').scroll_into_view_if_needed();await say(key)
        await page.select_option('#market','en');await page.click('#new');await page.check('#audioConsent');await page.select_option('#speaker','customer')
        await page.evaluate('replayEvidence("q4_customer.wav")');await say('live')
        live_rows=await page.evaluate('getLatencyRows()');(ROOT/'evidence/browser_latency.json').write_text(json.dumps(live_rows,indent=2),encoding='utf-8')
        await page.screenshot(path=str(ROOT/'evidence/live_screenshot.png'),full_page=True)
        await page.click('#new');await page.select_option('#speaker','agent');await page.evaluate('replayEvidence("q4_agent.wav")');await say('compliance')
        await page.goto('http://127.0.0.1:8765/static/overview.html');await say('limits')
        await context.close();video=ROOT/'runtime/narrated_raw.webm';await page.video.save_as(str(video));await browser.close()
    narration=ROOT/'runtime/narration.wav';narration.write_bytes(wav_bytes(np.concatenate(audio_parts)))
    output=ROOT/'evidence/narrated_walkthrough.mp4'
    result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(video),'-i',str(narration),'-c:v','libx264','-preset','fast','-crf','26','-c:a','aac','-shortest','-movflags','+faststart',str(output)],capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr[-2000:])
    (ROOT/'evidence/walkthrough_sections.json').write_text(json.dumps({'disclosure':'Synthetic narrator; automated recording of actual running UI. Not the candidate voice.','sections':timeline},indent=2),encoding='utf-8')
    print('Saved narrated_walkthrough.mp4',round(output.stat().st_size/1e6,1),'MB',flush=True)

if __name__=='__main__':asyncio.run(main())
