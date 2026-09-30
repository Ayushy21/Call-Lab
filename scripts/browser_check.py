import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        context=await browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(ROOT/'runtime/video'))
        page=await context.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto('http://127.0.0.1:8765');await page.click('#new');await page.wait_for_selector('.message')
        for text in ['Yes','Yes, I built a Python app','25 hours','Actually 10 hours','Yes','What is the weather on Mars?','human please']:
            count=await page.locator('.message').count();await page.fill('#text',text);await page.click('#turn button')
            await page.wait_for_function('(n)=>document.querySelectorAll(".message").length>=n+2',arg=count)
        assert 'human help' in await page.locator('.message').last.inner_text()
        await page.fill('#query','What are the eligibility requirements?');await page.click('#search button');await page.wait_for_selector('.result')
        assert 'Qualification' in await page.locator('.result').first.inner_text()
        await page.screenshot(path=str(ROOT/'evidence/app_screenshot.png'),full_page=True)
        # Demonstrate live audio when its fixture exists.
        if (ROOT/'evidence/q4_customer.wav').exists():
            await page.click('#new');await page.check('#audioConsent')
            await page.evaluate('replayEvidence("q4_customer.wav")')
            await page.wait_for_timeout(26000)
            rows=await page.evaluate('getLatencyRows()')
            (ROOT/'evidence/browser_latency.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
            await page.screenshot(path=str(ROOT/'evidence/live_screenshot.png'),full_page=True)
        for market,consent,question in [('ph','opo','Mahal po, wala akong pambayad'),('id','iya','Berapa denda kalau terlambat?')]:
            await page.select_option('#market',market);await page.click('#new');await page.wait_for_timeout(500)
            for text in [consent,question]:
                count=await page.locator('.message').count();await page.fill('#text',text);await page.click('#turn button')
                await page.wait_for_function('(n)=>document.querySelectorAll(".message").length>=n+2',arg=count)
            await page.wait_for_timeout(1300)
        await context.close()
        await page.video.save_as(str(ROOT/'evidence/walkthrough.webm'))
        await browser.close()
        (ROOT/'evidence/browser_test.json').write_text(json.dumps({'page_errors':errors,'passed':not errors,'video_note':'Automated silent browser walkthrough; no human narration.'},indent=2),encoding='utf-8')
        assert not errors,errors
        print('Browser smoke test passed; screenshot and silent walkthrough saved.')

if __name__=='__main__':asyncio.run(main())
