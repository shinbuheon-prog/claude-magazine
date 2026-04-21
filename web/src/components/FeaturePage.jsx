import React from 'react';
import { THEME, TYPE } from '../theme';

/**
 * 기획 특집 페이지 (TASK_022 섹션 C)
 * props.featureData = {
 *   category: "FEATURE",
 *   issueTag: "Cover Story",
 *   title: "특집 제목",
 *   lede: "리드 문장",
 *   author: "편집팀",
 *   sections: [ { heading, body, pullQuote, image }, ... ],
 *   sourceIds: ["src-001", "src-002"],
 * }
 */
const FeaturePage = ({ featureData = {} }) => {
  const {
    category = "FEATURE",
    issueTag = "Cover Story",
    title = "Claude 4 시대, 우리는 무엇을 다시 배워야 하는가",
    lede = "에이전트가 코드를 쓰고, 컨텍스트가 책 한 권을 삼키는 시대. 실무자들은 지난 1년간 어떤 습관을 버리고 어떤 감각을 새로 갖추게 되었는가.",
    author = "Claude Magazine 편집팀",
    sections = [
      {
        heading: "1. 컨텍스트는 더 이상 희소 자원이 아니다",
        body: "2024년까지만 해도 프롬프트 엔지니어의 핵심 업무는 '무엇을 잘라낼 것인가'였다. 토큰은 비쌌고, 맥락은 부족했으며, 요약은 반드시 지불해야 할 세금이었다. 그러나 1M 컨텍스트가 일상이 된 지금, 문제는 반대가 되었다. 넣을 수 있는 모든 것을 넣었을 때, 모델이 정말로 중요한 몇 줄에 집중하도록 만드는 기술, 즉 '컨텍스트 큐레이션'이 새로운 핵심 역량으로 떠올랐다. 실무자들은 이제 무엇을 넣을지가 아니라 무엇을 강조할지를 고민한다.",
        pullQuote: "문제는 넣을 수 없는 것이 아니라, 넣은 것들 중 무엇에 주목시킬 것인가가 되었다.",
        image: "/covers/default.png",
      },
      {
        heading: "2. 에이전트는 주니어가 아니라 동료다",
        body: "초기의 AI 코딩 도구는 '빠른 주니어' 비유로 설명되었다. 시키면 하고, 실수하면 고치게 하는 존재. 그러나 Claude Code처럼 긴 세션을 유지하면서 테스트·린트·문서화를 스스로 연쇄 수행하는 에이전트가 등장하자 비유가 무너졌다. 실무자들은 에이전트를 '검토받을 산출물을 내는 동료'로 다루기 시작했다. 역할은 위임이 아니라 공동 저자에 가깝다. 코드 리뷰에서 사람이 찾아야 할 것은 버그가 아니라 트레이드오프다.",
        pullQuote: "위임이 아니다. 공동 저자다.",
      },
      {
        heading: "3. 비용은 모델 단가가 아니라 사람 시간이다",
        body: "Sonnet 출력 단가는 3년째 동결, Opus는 지속 하락. 그러나 조직의 월간 AI 지출은 오히려 늘었다. 이유는 단순하다. 사람들이 더 많이, 더 깊이 쓰기 때문이다. 실무팀이 추적해야 할 지표는 토큰 단가가 아니라 '한 명의 엔지니어가 일주일에 AI를 통해 절감한 반복 작업 시간'이다. 이 값이 구독료의 5배를 넘지 않는다면, 문제는 모델이 아니라 워크플로에 있다.",
        pullQuote: "구독료의 5배를 넘지 못하는 절감은, 모델이 아니라 워크플로의 실패다.",
      },
    ],
    sourceIds = ["src-001", "src-003", "src-interview-001", "src-review-001"],
  } = featureData;

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      {/* 1. 헤드라인 + 리드 + 작가 크레딧 */}
      <header className="px-12 pt-14 pb-10">
        <div className="flex items-center gap-3 mb-6">
          <span
            className="inline-block px-3 py-1 rounded-full text-[10px] font-bold tracking-widest text-white"
            style={{ backgroundColor: THEME.primary }}
          >
            {category}
          </span>
          <span className={TYPE.category} style={{ color: THEME.accent }}>
            {issueTag}
          </span>
        </div>

        <h1
          className="text-5xl font-extrabold tracking-tight leading-[1.1] mb-6"
          style={{ color: THEME.textMain }}
        >
          {title}
        </h1>

        <p
          className="text-lg leading-relaxed italic max-w-[620px]"
          style={{ color: THEME.textSub }}
        >
          {lede}
        </p>

        <p className={`${TYPE.caption} mt-6`}>
          GLOBAL · {author} · {new Date().getFullYear()}
        </p>
      </header>

      <hr className="mx-12 border-gray-100" />

      {/* 2. 섹션 반복 */}
      <main className="px-12 py-10 space-y-14">
        {sections.map((sec, idx) => (
          <section key={idx}>
            {/* 소제목 */}
            <h2
              className="text-2xl font-bold tracking-tight mb-5"
              style={{ color: THEME.primary }}
            >
              {sec.heading}
            </h2>

            {/* 본문 (2단 컬럼) */}
            <div
              className="text-sm leading-relaxed columns-2 gap-8 mb-6"
              style={{ color: THEME.textMain }}
            >
              {sec.body}
            </div>

            {/* 선택적 이미지 */}
            {sec.image && (
              <figure className="mb-6">
                <img
                  src={sec.image}
                  alt={sec.heading}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  className="w-full h-48 object-cover rounded-lg shadow-sm"
                />
              </figure>
            )}

            {/* Pull quote */}
            {sec.pullQuote && (
              <blockquote
                className="border-l-4 pl-5 py-3 italic text-xl leading-relaxed max-w-[620px] mx-auto"
                style={{ borderLeftColor: THEME.accent, color: THEME.primary }}
              >
                "{sec.pullQuote}"
              </blockquote>
            )}
          </section>
        ))}
      </main>

      {/* 3. 사용 source_ids 요약 */}
      <section
        className="mx-12 mb-6 p-5 rounded-lg border-l-4"
        style={{ backgroundColor: THEME.bgLight, borderLeftColor: THEME.accentAlt }}
      >
        <p className="text-xs font-bold mb-2" style={{ color: THEME.primary }}>
          참고 소스
        </p>
        <p className="text-[11px] leading-relaxed" style={{ color: THEME.textSub }}>
          {sourceIds.map((id, idx) => (
            <span key={id}>
              <span className="font-bold" style={{ color: THEME.accent }}>[{id}]</span>
              {idx < sourceIds.length - 1 && <span className="mx-2">·</span>}
            </span>
          ))}
        </p>
      </section>

      {/* 4. AI 사용 고지 */}
      <div className="px-12">
        <div className="ai-disclosure" data-disclosure-slot="feature">
          <h4>AI 사용 고지</h4>
          <p>
            본 특집은 Claude를 활용해 자료 수집·초안 작성을 보조했으며,
            구성·문장·주장은 편집팀이 최종 책임집니다.
          </p>
        </div>
      </div>

      {/* 5. 푸터 */}
      <footer className="px-12 py-5 mt-4 border-t border-gray-100 flex justify-between items-center">
        <span className={`${TYPE.caption} font-bold`}>FEATURE · {issueTag}</span>
        <span className={TYPE.caption}>AI 사용 · 편집자 최종 검수</span>
      </footer>
    </div>
  );
};

export default FeaturePage;
