import puppeteer from 'file:///C:/AI-BS/tools/chrome-devtools-mcp/chrome-devtools-mcp-main/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';

async function test() {
  const defaultIgnore = [
    '--enable-automation',
    '--disable-sync',
    '--password-store=basic',
    '--use-mock-keychain',
  ];

  const browser = await puppeteer.launch({
    channel: 'chrome',
    headless: true,
    userDataDir: 'C:/Users/footb/.cache/chrome-devtools-mcp/chrome-profile',
    args: [
      '--disable-blink-features=AutomationControlled',
      '--profile-directory=Default',
      '--hide-crash-restore-bubble'
    ],
    ignoreDefaultArgs: defaultIgnore
  });

  const page = await browser.newPage();
  const webdriver = await page.evaluate(() => navigator.webdriver);
  console.log('navigator.webdriver:', webdriver);

  await page.goto('https://www.google.com', { waitUntil: 'networkidle2', timeout: 30000 });
  const cookies = await page.cookies('https://www.google.com');
  console.log('Google cookies count:', cookies.length);
  const cookieNames = cookies.map(c => c.name);
  console.log('Google cookie names:', cookieNames.join(', '));
  const hasAuthCookie = cookieNames.includes('SID') || cookieNames.includes('SAPISID') || cookieNames.includes('SSID');
  console.log('Has Google auth cookies (SID/SSID/SAPISID)?:', hasAuthCookie);

  await browser.close();
}

test().catch(err => {
  console.error('Error during test:', err);
  process.exit(1);
});
