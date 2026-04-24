import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, LabelList,
} from 'recharts';
import { THEME, TYPE } from '../theme';

/**
 * 리뷰 페이지 (TASK_022 섹션 B)
 * props.reviewData = {
 *   category: "TOOLS",
 *   productName: "Claude Code",
 *   verdict: "에디터 추천" | "조건부 추천" | "대안 고려",
 *   overallScore: 8.5,                      // 0~10
 *   criteria: [ { name, score, note }, ... ],
 *   prosText: ["..."], consText: ["..."],
 *   competitorTable: [ { name, price, rating }, ... ],
 *   summary: "한 줄 요약",
 *   sourceId: "src-review-001",
 * }
 */
const VERDICT_MAP = {
  "에디터 추천":   { bg: THEME.lineC,     label: "EDITOR'S CHOICE" },
  "조건부 추천":   { bg: THEME.accentAlt, label: "CONDITIONAL" },
  "대안 고려":     { bg: THEME.accent,    label: "CONSIDER ALT." },
};

const ReviewPage = ({ reviewData = {} }) => {
  const {
    category = "TOOLS",
    productName = "Claude Code",
    verdict = "에디터 추천",
    overallScore = 8.6,
    summary = "터미널 기반 AI 코딩 에이전트의 새로운 기준",
    criteria = [
      { name: "사용성",   score: 9, note: "직관적 CLI" },
      { name: "비용 효율", score: 7, note: "Pro 플랜 필요" },
      { name: "확장성",   score: 9, note: "MCP 서버 지원" },
      { name: "신뢰성",   score: 8, note: "롱런 세션 안정" },
      { name: "문서화",   score: 9, note: "공식 가이드 충실" },
    ],
    prosText = [
      "터미널 워크플로와 즉시 통합되는 네이티브 CLI 경험",
      "MCP 생태계로 외부 도구·DB·API까지 자연스럽게 확장",
      "롱 컨텍스트(1M) 지원으로 대형 코드베이스 분석 가능",
    ],
    consText = [
      "Pro 이상 구독이 사실상 필수",
      "고급 워크플로는 학습 곡선이 존재",
    ],
    competitorTable = [
      { name: "Claude Code",       price: "$20/mo",  rating: "8.6" },
      { name: "GitHub Copilot",    price: "$10/mo",  rating: "7.8" },
      { name: "Cursor",            price: "$20/mo",  rating: "8.2" },
      { name: "Windsurf",          price: "$15/mo",  rating: "7.5" },
    ],
    sourceId = "src-review-001",
  } = reviewData;

  const v = VERDICT_MAP[verdict] || VERDICT_MAP["에디터 추천"];

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      {/* 1. 헤더: 카테고리 + 제품명 + 종합점수 */}
      <header className="px-12 pt-12 pb-6 flex justify-between items-end">
        <div>
          <p className={`${TYPE.category} mb-3`} style={{ color: THEME.accent }}>
            [ REVIEW · {category} ]
          </p>
          <h1 className={TYPE.headline} style={{ color: THEME.textMain }}>
            {productName}
          </h1>
          <p className="mt-2 text-sm italic" style={{ color: THEME.textSub }}>
            {summary}
          </p>
        </div>
        <div className="text-right shrink-0 ml-6">
          <p className="text-[10px] tracking-widest font-bold text-gray-400 mb-1">
            OVERALL
          </p>
          <p
            className="text-6xl font-black leading-none"
            style={{ color: THEME.primary }}
          >
            {Number(overallScore).toFixed(1)}
          </p>
          <p className="text-xs text-gray-400 mt-1">/ 10.0</p>
        </div>
      </header>

      <hr className="mx-12 border-gray-100" />

      {/* 2. 평가 기준 차트 + 평결 배지 */}
      <section className="px-12 py-8 grid grid-cols-12 gap-6">
        {/* 좌측 8: 평가 기준 수평 바 차트 */}
        <div
          className="col-span-8 p-5 rounded-xl border"
          style={{ backgroundColor: THEME.bgLight, borderColor: '#E5E7EB' }}
        >
          <h3 className="text-xs font-bold text-gray-400 flex items-center gap-2 mb-4">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: THEME.accent }}
            />
            평가 기준별 점수
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={criteria}
                layout="vertical"
                margin={{ top: 4, right: 30, left: 0, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  domain={[0, 10]}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#9CA3AF' }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: THEME.textMain, fontWeight: 'bold' }}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: '8px',
                    border: 'none',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                    fontSize: '12px',
                  }}
                  formatter={(val, _name, props) => [
                    `${val} / 10 — ${props.payload.note || ''}`,
                    '점수',
                  ]}
                />
                <Bar dataKey="score" fill={THEME.accent} radius={[0, 6, 6, 0]} barSize={18}>
                  <LabelList
                    dataKey="score"
                    position="right"
                    style={{ fontSize: 11, fontWeight: 'bold', fill: THEME.primary }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 우측 4: 평결 배지 + 한 줄 요약 */}
        <div className="col-span-4 flex flex-col justify-between">
          <div
            className="p-5 rounded-xl text-white text-center shadow-md"
            style={{ backgroundColor: v.bg }}
          >
            <p className="text-[10px] tracking-[0.3em] font-bold opacity-80 mb-2">
              VERDICT
            </p>
            <p className="text-2xl font-black leading-tight">
              {verdict}
            </p>
            <p className="text-[10px] tracking-widest mt-2 opacity-70">
              {v.label}
            </p>
          </div>
          <div
            className="mt-4 p-4 rounded-lg border-l-2 text-xs leading-relaxed"
            style={{ borderLeftColor: THEME.primary, backgroundColor: `${THEME.primary}08`, color: THEME.textSub }}
          >
            편집부는 <strong style={{ color: THEME.primary }}>{criteria.length}개 기준</strong>에 따라
            종합 <strong style={{ color: THEME.accent }}>{Number(overallScore).toFixed(1)}점</strong>을
            부여했습니다.
          </div>
        </div>
      </section>

      {/* 3. Pros / Cons 2컬럼 */}
      <section className="px-12 pb-8 grid grid-cols-2 gap-6">
        {/* Pros */}
        <div
          className="p-5 rounded-xl"
          style={{ backgroundColor: `${THEME.lineC}10`, border: `1px solid ${THEME.lineC}33` }}
        >
          <span
            className="inline-block px-3 py-1 rounded-full text-[10px] font-bold tracking-widest text-white mb-3"
            style={{ backgroundColor: THEME.lineC }}
          >
            PROS
          </span>
          <ul className="text-sm space-y-2" style={{ color: THEME.textMain }}>
            {prosText.map((p, idx) => (
              <li key={idx} className="flex items-start">
                <span className="mr-2 mt-0.5 font-bold" style={{ color: THEME.lineC }}>+</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Cons */}
        <div
          className="p-5 rounded-xl"
          style={{ backgroundColor: `${THEME.accent}10`, border: `1px solid ${THEME.accent}33` }}
        >
          <span
            className="inline-block px-3 py-1 rounded-full text-[10px] font-bold tracking-widest text-white mb-3"
            style={{ backgroundColor: THEME.accent }}
          >
            CONS
          </span>
          <ul className="text-sm space-y-2" style={{ color: THEME.textMain }}>
            {consText.map((c, idx) => (
              <li key={idx} className="flex items-start">
                <span className="mr-2 mt-0.5 font-bold" style={{ color: THEME.accent }}>−</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 4. 경쟁 제품 비교 테이블 */}
      <section className="px-12 pb-8">
        <h3
          className="text-sm font-bold mb-4 flex items-center"
          style={{ color: THEME.primary }}
        >
          <span
            className="w-2 h-2 rounded-full mr-2"
            style={{ backgroundColor: THEME.accentAlt }}
          />
          경쟁 제품 비교
        </h3>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr
              className="text-left text-xs uppercase tracking-wider"
              style={{ backgroundColor: THEME.bgLight, color: THEME.textSub }}
            >
              <th className="py-3 px-4">제품</th>
              <th className="py-3 px-4">가격</th>
              <th className="py-3 px-4 text-right">종합 점수</th>
            </tr>
          </thead>
          <tbody>
            {competitorTable.map((row, idx) => {
              const highlight = row.name === productName;
              return (
                <tr
                  key={idx}
                  className="border-b border-gray-100"
                  style={highlight ? { backgroundColor: `${THEME.accent}10` } : undefined}
                >
                  <td
                    className="py-3 px-4 font-bold"
                    style={{ color: highlight ? THEME.accent : THEME.textMain }}
                  >
                    {row.name}
                    {highlight && (
                      <span className="ml-2 text-[10px] font-bold" style={{ color: THEME.accent }}>
                        ★ 본 리뷰
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4" style={{ color: THEME.textSub }}>{row.price}</td>
                  <td
                    className="py-3 px-4 text-right font-black"
                    style={{ color: THEME.primary }}
                  >
                    {row.rating}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* 5. AI 사용 고지 */}
      <div className="px-12">
        <div className="ai-disclosure" data-disclosure-slot="review">
          <h4>리뷰 기준 및 AI 사용 고지</h4>
          <p>
            본 리뷰는 5개 기준(사용성·비용·확장성·신뢰성·문서화)의 가중 평균으로 채점되며,
            Claude를 활용해 공식 문서·공개 벤치마크 데이터를 정리했습니다.
            모든 점수와 평결은 편집팀이 최종 검수했습니다.
          </p>
        </div>
      </div>

      {/* 6. 푸터 */}
      <footer className="px-12 py-5 mt-4 border-t border-gray-100 flex justify-between items-center">
        <span className={`${TYPE.caption} font-bold`}>REVIEW · {category}</span>
        <span className={TYPE.caption}>
          [{sourceId}] · AI 사용 · 편집자 최종 검수
        </span>
      </footer>
    </div>
  );
};

export default ReviewPage;
