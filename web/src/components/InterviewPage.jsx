import React from 'react';
import { THEME, TYPE } from '../theme';

/**
 * 인터뷰 페이지 (TASK_022 섹션 A)
 * props.interviewData = {
 *   interviewNum: "01",
 *   subject: "홍길동",
 *   role: "AI 프로덕트 리드",
 *   company: "Example Corp",
 *   quote: "핵심 발언 한 줄 인용",
 *   qa: [ { q: "질문", a: "답변 본문...", sourceId: "src-..." }, ... ],
 *   portraitUrl: "/covers/default.png",
 *   sourceId: "src-interview-001",
 * }
 */
const InterviewPage = ({ interviewData = {} }) => {
  const {
    interviewNum = "01",
    subject = "김지우",
    role = "AI 엔지니어링 리드",
    company = "Classmethod Korea",
    quote = "Claude Code는 단순한 AI 비서가 아니라 시니어 엔지니어의 두 번째 두뇌입니다.",
    qa = [
      {
        q: "Claude Code를 실무에 도입하면서 가장 크게 바뀐 점은 무엇인가요?",
        a: "코드 리뷰 사이클이 절반으로 줄었습니다. 에이전트가 린트·타입·테스트 스모크를 먼저 통과시키기 때문에 사람 리뷰어는 설계와 트레이드오프에만 집중할 수 있어요. 결과적으로 PR 머지까지의 리드타임이 평균 3.2일에서 1.5일로 단축됐습니다.",
        sourceId: "src-interview-001",
      },
      {
        q: "하루 업무에서 Claude를 어떻게 활용하시나요?",
        a: "아침 스탠드업 직후 에이전트에게 어제 남은 PR·이슈 요약을 맡기고, 오후에는 MCP로 연결된 내부 문서를 기반으로 설계 초안을 씁니다. 긴 글쓰기보다 반복 구조가 있는 리팩터링에서 특히 생산성이 크게 올라갑니다.",
        sourceId: "src-interview-002",
      },
      {
        q: "주니어 엔지니어에게 추천하는 사용 습관이 있다면?",
        a: "명세를 먼저 쓰고, 에이전트에게 스켈레톤과 테스트부터 뽑게 하세요. 완성 코드를 받아쓰지 말고, 실패한 테스트를 보면서 '왜 실패했는가'를 직접 추적하는 훈련을 해야 실력이 늡니다. AI는 속도를 주지만 이해는 사람이 쌓아야 합니다.",
        sourceId: "src-interview-003",
      },
    ],
    portraitUrl = "/covers/default.png",
    sourceId = "src-interview-001",
  } = interviewData;

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      {/* 1. 헤더 */}
      <header className="px-12 pt-12">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-[1px]" style={{ backgroundColor: THEME.accent }} />
          <p className={TYPE.category} style={{ color: THEME.accent }}>
            Interview {interviewNum}
          </p>
        </div>
      </header>

      {/* 2. 상단: 포트레이트 + 인물 정보 */}
      <section className="px-12 pt-4 pb-8 grid grid-cols-12 gap-8 items-center">
        {/* 좌측: 원형 포트레이트 */}
        <div className="col-span-5 flex justify-center">
          <div
            className="w-[260px] h-[260px] rounded-full overflow-hidden shadow-lg"
            style={{ border: `4px solid ${THEME.primary}` }}
          >
            <img
              src={portraitUrl}
              alt={subject}
              onError={(e) => { e.currentTarget.src = "/covers/default.png"; }}
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* 우측: 이름·직책·회사·인용문 */}
        <div className="col-span-7">
          <h1 className={TYPE.headline} style={{ color: THEME.textMain }}>
            {subject}
          </h1>
          <p className="mt-2 text-sm font-bold" style={{ color: THEME.accent }}>
            {role}
          </p>
          <p className="text-xs text-gray-400 mb-6">{company}</p>

          <blockquote
            className="border-l-4 pl-4 py-2 italic text-base leading-relaxed"
            style={{ borderLeftColor: THEME.accent, color: THEME.textMain }}
          >
            "{quote}"
          </blockquote>
        </div>
      </section>

      <hr className="mx-12 border-gray-100" />

      {/* 3. 본문: Q&A 반복 */}
      <main className="px-12 py-10 space-y-10">
        {qa.map((item, idx) => (
          <div key={idx} className="space-y-3">
            <p
              className="text-base font-bold leading-snug flex gap-3"
              style={{ color: THEME.primary }}
            >
              <span
                className="inline-block text-xl font-black shrink-0"
                style={{ color: THEME.accent }}
              >
                Q{idx + 1}.
              </span>
              <span>{item.q}</span>
            </p>
            <p className={`${TYPE.body} pl-8`} style={{ color: THEME.textMain }}>
              <span className="font-black mr-2" style={{ color: THEME.primary }}>A.</span>
              {item.a}
            </p>
            {item.sourceId && (
              <p className={`${TYPE.caption} pl-8`}>
                [{item.sourceId}]
              </p>
            )}
          </div>
        ))}
      </main>

      {/* 4. AI 사용 고지 hook (editorial_lint 연동 지점) */}
      <div className="px-12">
        <div className="ai-disclosure" data-disclosure-slot="interview">
          <h4>AI 사용 고지</h4>
          <p>
            본 인터뷰는 실제 취재 녹취를 기반으로 하며, Claude를 활용해 문장 정제·요약을 보조했습니다.
            최종 발언 확인 및 팩트체크는 편집자가 수행했습니다.
          </p>
        </div>
      </div>

      {/* 5. 푸터 */}
      <footer className="px-12 py-5 mt-4 border-t border-gray-100 flex justify-between items-center">
        <div className="flex space-x-4 items-center">
          <span className={TYPE.caption}>
            {String(interviewNum).padStart(2, '0')}
          </span>
          <span className={`${TYPE.caption} font-bold`}>INTERVIEW</span>
        </div>
        <span className={TYPE.caption}>
          [{sourceId}] · AI 사용 · 편집자 최종 검수
        </span>
      </footer>
    </div>
  );
};

export default InterviewPage;
