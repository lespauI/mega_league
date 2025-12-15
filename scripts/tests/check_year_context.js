const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', (m) => console.log('console:', m.type(), m.text()));
  await page.goto('http://127.0.0.1:8000/docs/roster_cap_tool/');
  const initial = await page.evaluate(() => document.body.innerHTML);
  console.log('initial body contains year-context?', initial.includes('id=\"year-context\"'));
  await page.waitForSelector('#cap-summary .metric:has-text("Cap Space") .value');
  const headerHtml = await page.$eval('#app-header', (el) => el.innerHTML);
  console.log('header html length:', headerHtml.length);
  console.log(headerHtml);
  const yc = await page.$('#year-context');
  console.log('has #year-context?', !!yc);
  if (yc) {
    const html = await page.$eval('#year-context', (el) => el.innerHTML);
    console.log('year-context html length:', html.length);
    console.log(html);
    const hasLabel = await page.$('[data-testid="year-context-label"]');
    console.log('has label?', !!hasLabel);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
