import React from 'react';
import { THEME, TYPE } from '../theme';

/**
 * 기사 본문 페이지 (EditableReportPage 패턴 적용)
 * props.pageData = {
 *   category: "DEEP DIVE",
 *   pageNum: "01",
 *   title: "Claude Sonnet 4.6, 실무에서 어떻게 쓸 것인가",
 *   infoTable: [{ label: "모델", value: "claude-sonnet-4-6" }, ...],
 *   quote: "effort=medium 하나로 비용을 30% 줄이면서 품질을 유지할 수 있다.",
 *   barData: { leftLabel: "Sonnet", rightLabel: "Opus", leftPct: 72 },
 *   bullets: ["기사 브리프·초안 생성에 최적", "1M 컨텍스트 베타 지원"],
 *   sourceId: "src-001",
 *   sourceNote: "Anthropic 공식 가격 문서 기준, 2026-04-20",
 * }
 */
const ArticlePage = ({ pageData = {} }) => {
  const {
    category = "DEEP DIVE",
    pageNum = "01",
    title = "Claude Sonnet 4.6, 실무에서 어떻게 쓸 것인가",
    infoTable = [
      { label: "모델", value: "claude-sonnet-4-6" },
      { label: "입력 단가", value: "$3 / MTok" },
      { label: "출력 단가", value: "$15 / MTok" },
      { label: "컨텍스트", value: "200K (1M 베타)" },
    ],
    quote = "effort=medium 하나로 비용을 30% 줄이면서 품질을 유지할 수 있다.",
    barData = { leftLabel: "일반 기사", rightLabel: "심층 리포트", leftPct: 72 },
    bullets = [
      "기사 브리프·초안 생성에 최적화",
      "Batch API로 야간 처리 시 비용 50% 절감",
    ],
    sourceId = "src-001",
    sourceNote = "Anthropic 공식 문서 기준",
  } = pageData;

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif leading-relaxed border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      {/* 1. 헤더 */}
      <header className="px-12 pt-12 flex justify-between items-end">
        <div>
          <p className={`${TYPE.category} mb-2`} style={{ color: THEME.accent }}>
            [ {category} ]
          </p>
          <h1 className={TYPE.headline} style={{ color: THEME.textMain }}>
            {title}
          </h1>
        </div>
        <span className="text-5xl font-light text-gray-100 select-none">{pageNum}</span>
      </header>

      <hr className="mx-12 my-8 border-gray-100" />

      {/* 2. 본문 그리드 (원본 7+5 패턴) */}
      <main className="px-12 pb-16 grid grid-cols-12 gap-8">

        {/* 왼쪽: 정보 테이블 + 인용구 */}
        <div className="col-span-7">
          <section
            className="mb-8 p-6 rounded-lg border-l-4"
            style={{ backgroundColor: THEME.bgLight, borderLeftColor: THEME.primary }}
          >
            <h2 className="text-sm font-bold mb-4 flex items-center" style={{ color: THEME.primary }}>
              <span
                className="w-2 h-2 rounded-full mr-2"
                style={{ backgroundColor: THEME.accent }}
              />
              모델 스펙 요약
            </h2>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {infoTable.map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-200 last:border-0">
                    <td className="py-3 font-bold text-gray-400 w-28">{row.label}</td>
                    <td className="py-3 font-medium" style={{ color: THEME.textMain }}>
                      {row.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* 인용구 */}
          <blockquote
            className="border-l-2 pl-4 py-2 italic text-sm leading-relaxed"
            style={{ borderLeftColor: THEME.accent, color: THEME.textSub }}
          >
            "{quote}"
            <p className={`${TYPE.caption} mt-2 not-italic`}>
              [{sourceId}] {sourceNote}
            </p>
          </blockquote>
        </div>

        {/* 오른쪽: 용도별 비중 바 + 포인트 */}
        <div
          className="col-span-5 p-6 rounded-xl border"
          style={{ backgroundColor: `${THEME.primary}08`, borderColor: `${THEME.primary}18` }}
        >
          <h3
            className="text-center text-sm font-bold mb-6 underline underline-offset-8 decoration-1"
            style={{ color: THEME.primary }}
          >
            Sonnet 4.6 활용 분포
          </h3>

          {/* 수평 바 차트 (원본 패턴 그대로) */}
          <div className="w-full space-y-2 mb-8">
            <div className="flex justify-between text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
              <span>{barData.leftLabel}</span>
              <span>{barData.rightLabel}</span>
            </div>
            <div className="h-10 w-full flex rounded-full overflow-hidden shadow-inner">
              <div
                className="flex items-center justify-center text-white font-bold text-base"
                style={{ width: `${barData.leftPct}%`, backgroundColor: THEME.primary }}
              >
                {barData.leftPct}%
              </div>
              <div
                className="flex items-center justify-center text-white font-bold text-base"
                style={{ width: `${100 - barData.leftPct}%`, backgroundColor: THEME.accentAlt }}
              >
                {100 - barData.leftPct}%
              </div>
            </div>
          </div>

          {/* 포인트 목록 */}
          <ul className="text-xs space-y-3" style={{ color: THEME.textSub }}>
            {bullets.map((b, idx) => (
              <li key={idx} className="flex items-start">
                <span className="mr-2 mt-0.5" style={{ color: THEME.accent }}>▶</span>
                {b}
              </li>
            ))}
          </ul>
        </div>
      </main>

      {/* 3. 푸터 */}
      <footer
        className="px-12 py-4 flex justify-between items-center"
        style={{ backgroundColor: THEME.bgLight }}
      >
        <span className={TYPE.caption}>CLAUDE MAGAZINE · {new Date().getFullYear()}</span>
        <span className={TYPE.caption}>AI 사용 보조 · 편집자 최종 검수 완료</span>
      </footer>
    </div>
  );
};

export default ArticlePage;
