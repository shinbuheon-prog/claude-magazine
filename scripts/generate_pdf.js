/**
 * Claude Magazine — PDF 생성 스크립트
 *
 * 사용법:
 *   node generate_pdf.js                  # output/claude-magazine-YYYY-MM.pdf 생성
 *   node generate_pdf.js --month 2026-05  # 월 지정
 *   node generate_pdf.js --rebuild        # Vite 강제 재빌드 후 생성
 *
 * 전제 조건:
 *   scripts/ 에서 npm install 완료
 */

const puppeteer = require('puppeteer');
const { execSync } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

// ── 설정 ──────────────────────────────────────────────
const PORT = 4173;
const WEB_DIR = path.resolve(__dirname, '../web');
const DIST_DIR = path.join(WEB_DIR, 'dist');
const OUTPUT_DIR = path.resolve(__dirname, '../output');

const monthArg = (() => {
  const idx = process.argv.indexOf('--month');
  if (idx !== -1 && process.argv[idx + 1]) return process.argv[idx + 1];
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
})();

const forceRebuild = process.argv.includes('--rebuild');
const OUTPUT_FILE = path.join(OUTPUT_DIR, `claude-magazine-${monthArg}.pdf`);

// ── MIME 맵 ───────────────────────────────────────────
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.ico':  'image/x-icon',
  '.json': 'application/json',
  '.woff2':'font/woff2',
  '.woff': 'font/woff',
  '.ttf':  'font/ttf',
};

// ── 헬퍼 ──────────────────────────────────────────────
function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function buildVite() {
  console.log('📦 Vite 빌드 중...');
  execSync('npm run build', { cwd: WEB_DIR, stdio: 'inherit' });
  console.log('✅ 빌드 완료');
}

function startStaticServer(distDir, port) {
  const server = http.createServer((req, res) => {
    let urlPath = req.url.split('?')[0];
    if (urlPath === '/') urlPath = '/index.html';

    let filePath = path.join(distDir, urlPath);

    // SPA fallback
    if (!fs.existsSync(filePath)) filePath = path.join(distDir, 'index.html');

    const ext = path.extname(filePath);
    const mime = MIME[ext] || 'application/octet-stream';

    try {
      const data = fs.readFileSync(filePath);
      res.writeHead(200, { 'Content-Type': mime });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end('Not found');
    }
  });

  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => {
      console.log(`✅ 정적 서버 준비 완료 (http://localhost:${port})`);
      resolve(server);
    });
  });
}

// ── 메인 ──────────────────────────────────────────────
(async () => {
  ensureDir(OUTPUT_DIR);

  // 1. Vite 빌드
  if (forceRebuild || !fs.existsSync(path.join(DIST_DIR, 'index.html'))) {
    buildVite();
  } else {
    console.log('ℹ️  기존 dist 사용 (재빌드하려면 --rebuild 옵션 추가)');
  }

  // 2. Node 내장 HTTP 정적 서버 시작
  console.log(`🌐 정적 서버 시작 (port ${PORT})...`);
  const server = await startStaticServer(DIST_DIR, PORT);

  let browser;
  try {
    // 3. Puppeteer 실행
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--font-render-hinting=none'],
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 800, height: 1100, deviceScaleFactor: 2 });

    await page.goto(`http://localhost:${PORT}?print=1`, {
      waitUntil: 'networkidle0',
      timeout: 30000,
    });

    // Recharts 렌더링 + 구글 폰트 로드 대기
    await new Promise((r) => setTimeout(r, 1200));

    console.log('📄 PDF 캡처 중...');

    const pdfBuffer = await page.pdf({
      format: 'A4',
      printBackground: true,
      margin: { top: '0', bottom: '0', left: '0', right: '0' },
    });

    await page.close();

    // 4. 저장
    fs.writeFileSync(OUTPUT_FILE, pdfBuffer);
    console.log(`\n🎉 PDF 생성 완료!`);
    console.log(`   파일: ${OUTPUT_FILE}`);
    console.log(`   크기: ${(pdfBuffer.length / 1024).toFixed(1)} KB`);

  } finally {
    if (browser) await browser.close();
    server.close();
    console.log('🧹 서버 종료');
  }
})().catch((err) => {
  console.error('❌ 오류:', err.message);
  process.exit(1);
});
