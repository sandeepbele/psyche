import asyncio
from pyppeteer import launch
from pyppeteer_stealth import stealth

async def fetch_screenshot(url, path):
    browser = await launch(headless=True)
    page = await browser.newPage()
    await stealth(page)
    await page.goto(url)
    #await page.waitForSelector('html[data-livestyle-extension="available"]',{'timeout': 60000})

    await page.screenshot({'path': path,'fullPage': True})
    await browser.close()

#url = 'https://stabletether.net/'
url = 'https://www.coinbase.com'
imagename = 'coinbase.png'
path = '/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/'+imagename

asyncio.get_event_loop().run_until_complete(fetch_screenshot(url, path))