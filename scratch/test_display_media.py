import asyncio
from pyppeteer import launch

async def test():
    # Test 1: With --use-fake-ui-for-media-stream
    browser = await launch(
        executablePath=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=True,
        args=[
            '--use-fake-ui-for-media-stream',
            '--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173'
        ]
    )
    page = await browser.newPage()
    await page.goto('http://127.0.0.1:5173')
    
    result = await page.evaluate('''async () => {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
            return { success: true, tracks: stream.getVideoTracks().length, label: stream.getVideoTracks()[0].label };
        } catch (e) {
            return { success: false, error: e.name, message: e.message };
        }
    }''')
    print("Test 1 (with --use-fake-ui-for-media-stream):", result)
    await browser.close()

    # Test 2: With --auto-select-desktop-capture-source="Entire screen"
    browser2 = await launch(
        executablePath=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=True,
        args=[
            '--use-fake-ui-for-media-stream',
            '--auto-select-desktop-capture-source=Entire screen',
            '--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173'
        ]
    )
    page2 = await browser2.newPage()
    await page2.goto('http://127.0.0.1:5173')
    result2 = await page2.evaluate('''async () => {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
            return { success: true, tracks: stream.getVideoTracks().length, label: stream.getVideoTracks()[0].label };
        } catch (e) {
            return { success: false, error: e.name, message: e.message };
        }
    }''')
    print("Test 2 (with --auto-select-desktop-capture-source):", result2)
    await browser2.close()

    # Test 3: Without --use-fake-ui-for-media-stream
    browser3 = await launch(
        executablePath=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=True,
        args=[
            '--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173'
        ]
    )
    page3 = await browser3.newPage()
    await page3.goto('http://127.0.0.1:5173')
    result3 = await page3.evaluate('''async () => {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
            return { success: true, tracks: stream.getVideoTracks().length, label: stream.getVideoTracks()[0].label };
        } catch (e) {
            return { success: false, error: e.name, message: e.message };
        }
    }''')
    print("Test 3 (without fake-ui):", result3)
    await browser3.close()

asyncio.run(test())
