/**
 * Issue 0 Pilot Preview — 단독 HTML → PDF 1p 변환
 *
 * 사용:
 *   cd scripts && node render_preview_pdf.js
 *   → output/issue0_preview.pdf 생성 (A4 1p)
 */
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const HTML_PATH = path.resolve(__dirname, 'templates/issue0_preview.html');
const PDF_PATH = path.resolve(__dirname, '../output/issue0_preview.pdf');

(async () => {
  if (!fs.existsSync(HTML_PATH)) {
    console.error(`❌ HTML 파일 없음: ${HTML_PATH}`);
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 800, height: 1130, deviceScaleFactor: 2 });

    const fileUrl = `file://${HTML_PATH.replace(/\\/g, '/')}`;
    await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise((r) => setTimeout(r, 1500)); // 폰트 로딩 안정화

    await page.pdf({
      path: PDF_PATH,
      format: 'A4',
      printBackground: true,
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
      preferCSSPageSize: true,
    });

    const stats = fs.statSync(PDF_PATH);
    console.log(`✅ PDF 생성 완료: ${PDF_PATH}`);
    console.log(`   크기: ${(stats.size / 1024).toFixed(1)} KB`);
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error('❌ PDF 생성 실패:', err);
  process.exit(1);
});
