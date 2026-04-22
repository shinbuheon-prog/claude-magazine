import React from 'react';
import { THEME, TYPE } from '../theme';

/**
 * 편집자의 말 페이지
 * props.editorialData = {
 *   issue: "VOL.01",
 *   date: "2026년 5월",
 *   theme: "에이전트 시대의 실무 전환",
 *   greeting: "독자 여러분께",
 *   body: [
 *     "이번 호의 주제인 에이전트는...",
 *     "한편 비용 측면에서는...",
 *     "편집팀은 이번 호를 준비하며...",
 *   ],
 *   editorName: "편집장 이름",
 *   editorTitle: "Editor-in-Chief",
 * }
 */
const EditorialPage = ({ editorialData = {} }) => {
  const {
    issue = "VOL.01",
    date = "2026년 5월",
    theme = "에이전트 시대의 실무 전환",
    greeting = "독자 여러분께",
    body = [
      "이번 호의 주제는 에이전트 시대입니다. 단순 도구를 넘어 실제 업무를 대신 수행하는 AI가 등장하면서, 편집자·기획자·개발자의 일하는 방식이 바뀌고 있습니다.",
      "다만 에이전트가 대체할 수 없는 영역이 분명히 존재합니다. 이번 호는 바로 그 경계를 짚는 데 집중했습니다. 어느 업무를 맡기고, 어느 판단을 직접 해야 하는가.",
      "한 달의 작업 과정에서 21꼭지 기사 모두가 최소 한 번씩 편집팀의 손을 거쳤습니다. AI는 초안과 팩트체크를 돕되, 최종 문장과 판정은 사람이 책임집니다.",
    ],
    editorName = "편집장 이름",
    editorTitle = "Editor-in-Chief",
  } = editorialData;

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
            Editorial Letter · {issue} · {date}
          </p>
        </div>
        <h2 className={TYPE.headline} style={{ color: THEME.textMain }}>
          편집자의 말
        </h2>
        <p className="mt-3 text-sm italic" style={{ color: THEME.textSub }}>
          이번 호의 주제: {theme}
        </p>
      </header>

      <hr className="mx-12 border-gray-100" />

      {/* 본문 */}
      <main className="px-12 py-10">
        <p
          className="text-base font-bold mb-6"
          style={{ color: THEME.primary }}
        >
          {greeting}
        </p>

        <div className="space-y-5 text-base leading-relaxed" style={{ color: THEME.textMain }}>
          {body.map((paragraph, idx) => (
            <p key={idx}>{paragraph}</p>
          ))}
        </div>

        {/* 편집장 서명 블록 */}
        <div className="mt-12 flex items-end justify-end">
          <div className="text-right">
            <div
              className="text-3xl font-black italic mb-1"
              style={{ color: THEME.primary }}
            >
              {editorName}
            </div>
            <p className={TYPE.caption}>{editorTitle}</p>
            <p className={`${TYPE.caption} mt-1`}>{date}</p>
          </div>
        </div>
      </main>

      {/* 푸터 */}
      <footer className="px-12 py-4 border-t border-gray-100 flex justify-between items-center">
        <span className={TYPE.caption}>CLAUDE MAGAZINE · EDITORIAL</span>
        <span className={TYPE.caption}>{issue}</span>
      </footer>
    </div>
  );
};

export default EditorialPage;
