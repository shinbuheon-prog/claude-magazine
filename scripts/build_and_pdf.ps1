# Claude Magazine — 빌드 → PDF 원스톱 스크립트 (Windows PowerShell)
# 사용법: .\build_and_pdf.ps1 [-Month 2026-05]
param(
  [string]$Month = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Write-Host "`n=== Claude Magazine PDF 생성 ===" -ForegroundColor Cyan

# 1. web 의존성 설치
Push-Location "$Root\web"
if (-not (Test-Path "node_modules")) {
  Write-Host "📦 web 패키지 설치 중..." -ForegroundColor Yellow
  npm install
}

# 2. Vite 빌드
Write-Host "🔨 Vite 빌드 중..." -ForegroundColor Yellow
npm run build
Pop-Location

# 3. scripts 의존성 설치
Push-Location "$Root\scripts"
if (-not (Test-Path "node_modules")) {
  Write-Host "📦 scripts 패키지 설치 중..." -ForegroundColor Yellow
  npm install
}

# 4. PDF 생성
Write-Host "📄 PDF 생성 중..." -ForegroundColor Yellow
if ($Month) {
  node generate_pdf.js --month $Month
} else {
  node generate_pdf.js
}
Pop-Location

Write-Host "`n✅ 완료! output/ 폴더를 확인하세요." -ForegroundColor Green
