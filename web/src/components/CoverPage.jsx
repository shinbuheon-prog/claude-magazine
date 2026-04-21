import React from 'react';
import { THEME } from '../theme';

// 월간 커버 이미지 드롭인 경로 (TASK_021)
// Vite 는 web/public/ 하위 파일을 빌드 시 dist/ 로 그대로 복사한다.
const COVER_BASE = '/covers';
const DEFAULT_COVER = `${COVER_BASE}/default.png`;

/**
 * "2026년 5월" 형식의 한국어 날짜를 "/covers/2026-05.png" 로 정규화한다.
 * 매칭 실패 시 default.png 로 폴백.
 */
function resolveCoverPath(issueDate) {
  if (typeof issueDate !== 'string') return DEFAULT_COVER;
  const match = issueDate.match(/(\d{4})년\s*(\d{1,2})월/);
  if (!match) return DEFAULT_COVER;
  const yyyy = match[1];
  const mm = String(match[2]).padStart(2, '0');
  return `${COVER_BASE}/${yyyy}-${mm}.png`;
}

/**
 * 매거진 표지
 * props.coverData = {
 *   issue: "VOL.01",
 *   date: "2026년 5월",
 *   headline: "Claude 4 시대의 실무 전략",
 *   subline: "에이전트·컨텍스트·비용 최적화 완전 분석",
 *   tag: "특집",
 * }
 */
const CoverPage = ({ coverData = {} }) => {
  const {
    issue = "VOL.01",
    date = "2026년 5월",
    headline = "Claude 4 시대의\n실무 전략",
    subline = "에이전트·컨텍스트·비용 최적화 완전 분석",
    tag = "특집",
  } = coverData;

  const coverSrc = resolveCoverPath(date);

  return (
    <div
      className="max-w-[800px] h-[1100px] mx-auto relative overflow-hidden text-white font-serif shadow-2xl my-10"
      style={{ backgroundColor: THEME.primary }}
    >
      {/* 배경 장식 원 */}
      <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full opacity-5 bg-white" />
      <div className="absolute top-0 left-0 w-full h-1" style={{ backgroundColor: THEME.accent }} />

      {/* 1. 상단 메타 */}
      <div className="absolute top-14 left-12 flex items-center space-x-4">
        <span
          className="px-3 py-1 text-[10px] font-black tracking-[0.3em] uppercase rounded-full"
          style={{ backgroundColor: THEME.accent }}
        >
          Claude Magazine
        </span>
        <span className="text-sm font-light opacity-60 tracking-widest">{issue} · {date}</span>
      </div>

      {/* 2. 메인 타이틀 */}
      <div className="absolute top-[22%] left-12 z-10 max-w-[480px]">
        <p
          className="text-xs tracking-[0.4em] font-bold mb-4 uppercase"
          style={{ color: THEME.accent }}
        >
          [ {tag} ]
        </p>
        <h1 className="text-6xl font-black leading-[1.1] tracking-tight whitespace-pre-line mb-6">
          {headline}
        </h1>
        {/* 골드 구분선 (원본 패턴 유지) */}
        <div className="w-16 h-[3px] mb-6" style={{ backgroundColor: THEME.accent }} />
        <p className="text-base font-light leading-relaxed opacity-80 max-w-[360px]">
          {subline}
        </p>
      </div>

      {/* 3. 우하단 월간 커버 이미지 (TASK_021 드롭인) */}
      <div
        className="absolute bottom-0 right-0 w-[75%] h-[50%] rounded-tl-[80px] overflow-hidden border-l border-t"
        style={{ borderColor: 'rgba(255,255,255,0.08)', backgroundColor: 'rgba(255,255,255,0.04)' }}
      >
        <img
          src={coverSrc}
          alt={`${issue} ${date} 커버 일러스트`}
          className="w-full h-full object-cover"
          loading="eager"
          onError={(e) => {
            // 무한 루프 방지: 이미 default.png 로 교체된 경우 더 이상 시도하지 않는다.
            const img = e.currentTarget;
            if (img.dataset.fallback === '1') return;
            img.dataset.fallback = '1';
            img.src = DEFAULT_COVER;
          }}
        />
      </div>

      {/* 4. 하단 브랜딩 */}
      <div className="absolute bottom-10 left-12 flex items-center space-x-3">
        <div
          className="w-8 h-8 rounded flex items-center justify-center text-white text-xs font-black"
          style={{ backgroundColor: THEME.accent }}
        >
          C
        </div>
        <div>
          <p className="text-xs font-black tracking-widest uppercase">Claude Magazine</p>
          <p className="text-[10px] opacity-40 tracking-widest">Powered by Anthropic</p>
        </div>
      </div>
    </div>
  );
};

export default CoverPage;
