const { chromium } = require('playwright');
const { spawn } = require('child_process');
(async () => {
  const srv = spawn('python3', ['-m', 'http.server', '8010'], { cwd: process.cwd(), stdio: 'ignore' });
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8010/docs/roster_cap_tool/');
  const initial = await page.evaluate(() => document.body.innerHTML);
  console.log('initial has year-context?', initial.includes('id="year-context"'));
  await page.waitForSelector('#cap-summary .metric:has-text("Cap Space") .value');
  const header = await page.$eval('#app-header', el => el.innerHTML);
  console.log('header shows year-context?', header.includes('id="year-context"'));
  await browser.close();
  srv.kill();
})().catch((e) => { console.error(e); process.exit(1); });
