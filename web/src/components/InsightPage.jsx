import React from 'react';
import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { THEME, TYPE } from '../theme';

/**
 * 데이터 인사이트 페이지 (InsightReportPage 패턴 적용)
 * props.insightData = {
 *   insightNum: "01",
 *   title: "Claude API 비용 추이 분석 (2024-2026)",
 *   chartData: [
 *     { year: "'24 Q1", sonnet: 15, opus: 75 },
 *     { year: "'24 Q3", sonnet: 15, opus: 75 },
 *     { year: "'25 Q1", sonnet: 15, opus: 60 },
 *     { year: "'25 Q3", sonnet: 15, opus: 50 },
 *     { year: "'26 Q1", sonnet: 15, opus: 25 },
 *   ],
 *   statA: { label: "Sonnet 비용 변화", value: "동결", unit: "3년간" },
 *   statB: { label: "Opus 출력 단가", value: "-67%", unit: "2년 대비" },
 *   expertTip: "모델 비용보다 사람 시간과 구독 운영이 실제 병목입니다.",
 *   sourceId: "src-003",
 * }
 */
const InsightPage = ({ insightData = {} }) => {
  const {
    insightNum = "01",
    title = "Claude API 비용 추이 분석 (2024-2026)",
    chartData = [
      { year: "'24 Q1", sonnet: 15, opus: 75 },
      { year: "'24 Q3", sonnet: 15, opus: 75 },
      { year: "'25 Q1", sonnet: 15, opus: 60 },
      { year: "'25 Q3", sonnet: 15, opus: 50 },
      { year: "'26 Q1", sonnet: 15, opus: 25 },
    ],
    statA = { label: "Sonnet 출력 단가", value: "$15", unit: "3년간 동결" },
    statB = { label: "Opus 출력 단가", value: "$25", unit: "↓ 지속 하락" },
    expertTip = "모델 비용보다 사람 시간과 구독 운영이 실제 병목입니다. Batch API 활용으로 비용을 50% 절감하세요.",
    sourceId = "src-003",
  } = insightData;

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      {/* 1. 섹션 헤더 (원본 라인+번호 패턴) */}
      <header className="px-12 pt-12">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-[1px]" style={{ backgroundColor: THEME.accent }} />
          <p className={TYPE.category} style={{ color: THEME.accent }}>
            Insight {insightNum}
          </p>
        </div>
        <h2 className={TYPE.headline} style={{ color: THEME.textMain }}>
          {title}
        </h2>
      </header>

      {/* 2. 데이터 섹션 */}
      <main className="px-12 py-10">
        <div className="grid grid-cols-12 gap-8">

          {/* 차트 영역 */}
          <div
            className="col-span-8 p-6 rounded-2xl border shadow-sm"
            style={{ backgroundColor: THEME.bgLight, borderColor: '#E5E7EB' }}
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xs font-bold text-gray-400 flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: THEME.accent }}
                />
                출력 단가 추이 ($ / MTok)
              </h3>
              <span className="text-[10px] text-gray-300">Unit: USD/MTok</span>
            </div>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                  <XAxis
                    dataKey="year"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#9CA3AF' }}
                  />
                  <YAxis hide domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '8px',
                      border: 'none',
                      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                      fontSize: '12px',
                    }}
                    formatter={(v) => [`$${v}`, '']}
                  />
                  <Line
                    type="monotone"
                    dataKey="sonnet"
                    stroke={THEME.lineA}
                    strokeWidth={3}
                    dot={{ r: 5, fill: THEME.lineA }}
                    label={{ position: 'top', fontSize: 11, fontWeight: 'bold', fill: THEME.lineA }}
                    name="Sonnet (출력)"
                  />
                  <Line
                    type="monotone"
                    dataKey="opus"
                    stroke={THEME.lineB}
                    strokeWidth={3}
                    dot={{ r: 5, fill: THEME.lineB }}
                    label={{ position: 'top', fontSize: 11, fontWeight: 'bold', fill: THEME.lineB }}
                    name="Opus (출력)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {/* 범례 */}
            <div className="flex justify-center space-x-6 mt-4 text-[11px] font-bold text-gray-400">
              <span className="flex items-center gap-1.5">
                <i className="w-3 h-3 rounded-full" style={{ backgroundColor: THEME.lineA }} />
                Sonnet 출력
              </span>
              <span className="flex items-center gap-1.5">
                <i className="w-3 h-3 rounded-full" style={{ backgroundColor: THEME.lineB }} />
                Opus 출력
              </span>
            </div>
          </div>

          {/* 우측 지표 + 출처 */}
          <div className="col-span-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div
                className="p-4 border-l-2"
                style={{ borderLeftColor: THEME.accent, backgroundColor: `${THEME.accent}0D` }}
              >
                <p className="text-xs font-bold mb-1" style={{ color: THEME.accent }}>
                  {statA.label}
                </p>
                <p className="text-2xl font-black italic" style={{ color: THEME.textMain }}>
                  {statA.value}
                  <span className="text-xs font-normal text-gray-400 ml-1">{statA.unit}</span>
                </p>
              </div>
              <div className="p-4 border-l-2 border-gray-200 bg-gray-50">
                <p className="text-xs font-bold text-gray-400 mb-1">{statB.label}</p>
                <p className="text-2xl font-black italic text-gray-500">
                  {statB.value}
                  <span className="text-xs font-normal text-gray-400 ml-1">{statB.unit}</span>
                </p>
              </div>
            </div>
            <p className="text-[10px] leading-relaxed text-gray-400 mt-4">
              [{sourceId}] Anthropic 공식 가격표 기준.
              실제 운영 비용은 재시도·팩트체크 왕복을 포함해 2× 버퍼 권장.
            </p>
          </div>
        </div>

        {/* 3. 에디터 팁 박스 (원본 Expert Tip 패턴) */}
        <section
          className="mt-10 rounded-2xl p-8 text-white relative overflow-hidden"
          style={{ backgroundColor: THEME.primary }}
        >
          {/* 배경 장식 따옴표 */}
          <div className="absolute top-0 right-0 opacity-10 text-9xl font-black transform translate-x-1/4 -translate-y-1/4 select-none">
            "
          </div>
          <div className="relative z-10">
            <span
              className="inline-block px-3 py-1 rounded-full text-[10px] font-bold tracking-widest mb-4"
              style={{ backgroundColor: 'rgba(255,255,255,0.15)' }}
            >
              EDITOR TIP
            </span>
            <p className="text-base font-medium leading-relaxed italic mb-6 max-w-[520px]">
              "{expertTip}"
            </p>
            <p className="text-xs font-bold opacity-60">— Claude Magazine 편집팀</p>
          </div>
        </section>
      </main>

      {/* 4. 푸터 */}
      <footer className="px-12 py-5 border-t border-gray-100 flex justify-between items-center">
        <div className="flex space-x-4 items-center">
          <span className={TYPE.caption}>
            {String(insightNum).padStart(2, '0')}
          </span>
          <span className={`${TYPE.caption} font-bold`}>INSIGHT REPORT</span>
        </div>
        <span className={TYPE.caption}>AI 사용 · 편집자 최종 검수</span>
      </footer>
    </div>
  );
};

export default InsightPage;
