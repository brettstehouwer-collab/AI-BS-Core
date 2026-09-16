import sys
import argparse
import time
from playwright.sync_api import sync_playwright

def run_overlay(url: str, title: str):
    with sync_playwright() as p:
        # Launch Chromium in app mode (no url bar, no tabs)
        browser = p.chromium.launch(
            headless=False,
            args=[
                f"--app={url}",
                "--window-size=1920,1080",
                "--disable-infobars",
                "--hide-scrollbars"
            ]
        )
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Wait for page to load
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        
        # Force Title and Background Color (Chroma Key)
        # Using exact pure blue #0000FF for FFmpeg chromakey
        page.evaluate(f"document.title = '{title}'")
        page.evaluate("document.body.style.backgroundColor = '#0000FF'")
        page.evaluate("document.documentElement.style.backgroundColor = '#0000FF'")
        
        print(f"Overlay Worker Running: {title} mapped to {url}", flush=True)
        
        # Keep alive until terminated by parent process
        try:
            while True:
                # Ensure title stays constant (some SPAs change it dynamically)
                try:
                    page.evaluate(f"if(document.title !== '{title}') document.title = '{title}'")
                except Exception:
                    pass
                time.sleep(2.0)
        except KeyboardInterrupt:
            pass
        
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BS Browser Overlay Worker")
    parser.add_argument("--url", required=True, help="URL to render")
    parser.add_argument("--title", required=True, help="Window title for gdigrab to capture")
    args = parser.parse_args()
    
    run_overlay(args.url, args.title)
