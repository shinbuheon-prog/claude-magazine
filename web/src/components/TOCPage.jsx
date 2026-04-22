import React from 'react';
import { THEME, TYPE } from '../theme';

/**
 * 목차 페이지 (TOC)
 * props.tocData = {
 *   issue: "VOL.01",
 *   date: "2026년 5월",
 *   theme: "에이전트 시대의 실무 전환",
 *   sections: [
 *     {
 *       name: "FEATURE",
 *       articles: [{ title: "...", page: 4, slug: "..." }]
 *     },
 *     ...
 *   ]
 * }
 */
const TOCPage = ({ tocData = {} }) => {
  const {
    issue = "VOL.01",
    date = "2026년 5월",
    theme = "에이전트 시대의 실무 전환",
    sections = [
      {
        name: "FEATURE",
        articles: [{ title: "AI 에이전트 경제학", page: 4, slug: "agent-economics" }],
      },
      {
        name: "DEEP DIVE",
        articles: [
          { title: "Claude Sonnet 4.6 실무 활용법", page: 18 },
          { title: "Opus 4.7 비용 최적화 전략", page: 22 },
        ],
      },
      {
        name: "INSIGHT",
        articles: [
          { title: "Claude API 비용 추이 분석", page: 42 },
          { title: "AI 도구 업무 침투율", page: 45 },
        ],
      },
      {
        name: "INTERVIEW",
        articles: [{ title: "AI 프로덕트 리드 홍길동", page: 54 }],
      },
      {
        name: "REVIEW",
        articles: [{ title: "Claude Code 6개월 사용기", page: 69 }],
      },
    ],
  } = tocData;

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      {/* 헤더 */}
      <header className="px-12 pt-12 pb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-10 h-[1px]" style={{ backgroundColor: THEME.accent }} />
          <p className={TYPE.category} style={{ color: THEME.accent }}>
            Contents · {issue}
          </p>
        </div>
        <h2 className={TYPE.headline} style={{ color: THEME.textMain }}>
          목차
        </h2>
        <p className="mt-3 text-sm italic" style={{ color: THEME.textSub }}>
          {theme} · {date}
        </p>
      </header>

      <hr className="mx-12 border-gray-100" />

      {/* 섹션별 꼭지 */}
      <main className="px-12 py-10 space-y-8">
        {sections.map((section, sIdx) => (
          <section key={sIdx}>
            <div className="flex items-baseline space-x-3 mb-3">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: THEME.accent }}
              />
              <h3
                className={TYPE.category}
                style={{ color: THEME.primary }}
              >
                {section.name}
              </h3>
            </div>
            <ul className="space-y-2">
              {section.articles.map((article, aIdx) => (
                <li
                  key={aIdx}
                  className="flex items-baseline"
                  style={{ color: THEME.textMain }}
                >
                  <span className="font-medium text-base flex-shrink-0">
                    {article.title}
                  </span>
                  <span
                    className="flex-grow border-b border-dotted mx-3 mb-1"
                    style={{ borderColor: THEME.textLight }}
                  />
                  <span
                    className="font-black text-base flex-shrink-0"
                    style={{ color: THEME.primary }}
                  >
                    {String(article.page).padStart(3, ' ')}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </main>

      {/* 푸터 */}
      <footer className="px-12 py-4 border-t border-gray-100 flex justify-between items-center">
        <span className={TYPE.caption}>CLAUDE MAGAZINE · CONTENTS</span>
        <span className={TYPE.caption}>{issue} · {date}</span>
      </footer>
    </div>
  );
};

export default TOCPage;
