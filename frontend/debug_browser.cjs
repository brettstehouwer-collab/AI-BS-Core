const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => {
    console.log(`[Browser Console ${msg.type()}]`, msg.text());
  });
  
  page.on('pageerror', err => {
    console.error('[Browser Page Error]', err);
  });
  
  try {
    console.log("Navigating to http://localhost:5173 ...");
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    console.log("Navigation complete.");
    
    // Check if the page is rendering something
    const html = await page.content();
    console.log("Body length:", html.length);
    if (html.includes("ErrorBoundary")) {
      console.log("ErrorBoundary is visible on the page.");
    }
  } catch (err) {
    console.error("Navigation failed:", err);
  } finally {
    await browser.close();
  }
})();
