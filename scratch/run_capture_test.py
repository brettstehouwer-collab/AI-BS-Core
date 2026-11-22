import asyncio
from pyppeteer import launch

async def run_test():
    browser = await launch(
        executablePath=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=True,
        args=[
            '--use-fake-ui-for-media-stream',
            '--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173'
        ]
    )
    page = await browser.newPage()
    await page.goto('http://127.0.0.1:5173/test_capture.html')
    # Click the button with real user gesture
    await page.click('#btn')
    await asyncio.sleep(2)
    text = await page.evaluate("() => document.getElementById('output').innerText")
    print("Result with --use-fake-ui-for-media-stream:", text)
    await browser.close()

    # Test without --use-fake-ui-for-media-stream (headless might fail, but let's see what error)
    browser2 = await launch(
        executablePath=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=True,
        args=[
            '--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173'
        ]
    )
    page2 = await browser2.newPage()
    await page2.goto('http://127.0.0.1:5173/test_capture.html')
    await page2.click('#btn')
    await asyncio.sleep(2)
    text2 = await page2.evaluate("() => document.getElementById('output').innerText")
    print("Result without --use-fake-ui-for-media-stream:", text2)
    await browser2.close()

asyncio.run(run_test())
