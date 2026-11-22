import asyncio
import os
from pyppeteer import launch

profile_dir = os.path.expandvars(r"%LOCALAPPDATA%\AI_BS_Studio\DesktopProfile")

async def test_perms():
    browser = await launch(
        executablePath=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=False,
        args=[
            f'--user-data-dir={profile_dir}',
            '--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173'
        ]
    )
    page = await browser.newPage()
    await page.goto('http://127.0.0.1:5173/test_capture.html')
    
    # Test microphone
    mic_result = await page.evaluate('''async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const tracks = stream.getAudioTracks().map(t => t.label);
            stream.getTracks().forEach(t => t.stop());
            return { success: true, tracks };
        } catch (e) {
            return { success: false, error: e.name, message: e.message };
        }
    }''')
    print("Mic test without --use-fake-ui-for-media-stream (using DesktopProfile):", mic_result)
    
    await browser.close()

asyncio.run(test_perms())
