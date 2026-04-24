import React from 'react';
import { THEME, TYPE } from '../theme';

/**
 * 콜로폰 (뒷면 정보) 페이지
 * props.colophonData = {
 *   issue, date, publisher, editor, email,
 *   team: [{name, role}],
 *   contributors: [string],
 *   aiNotice: string,
 *   copyright: string,
 *   corrections: string,
 * }
 */
const ColophonPage = ({ colophonData = {} }) => {
  const {
    issue = "VOL.01",
    date = "2026년 5월",
    publisher = "Claude Magazine 편집부",
    editor = "편집장 이름",
    email = "editorial@claude-magazine.kr",
    team = [
      { name: "편집장 이름", role: "Editor-in-Chief" },
      { name: "시니어 에디터", role: "Senior Editor" },
      { name: "디자이너", role: "Art Director" },
      { name: "기자", role: "Staff Writer" },
    ],
    contributors = [],
    aiNotice = "본 매거진의 기사는 Claude AI 보조 도구(Sonnet 4.6, Opus 4.7, Haiku 4.5)를 활용해 초안·팩트체크·재가공을 지원받았습니다. 최종 편집·승인 책임은 Claude Magazine 편집팀에 있습니다.",
    copyright = "ⓒ 2026 Claude Magazine. All rights reserved. 본지 게재 콘텐츠의 무단 전재·재배포 금지.",
    corrections = "정정 요청은 24시간 내 1차 응답. editorial@claude-magazine.kr",
  } = colophonData;

  return (
    <div
      className="max-w-[800px] mx-auto bg-white shadow-2xl my-10 font-serif border-t-[10px]"
      style={{ borderColor: THEME.primary }}
    >
      <header className="px-12 pt-12 pb-4">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-10 h-[1px]" style={{ backgroundColor: THEME.accent }} />
          <p className={TYPE.category} style={{ color: THEME.accent }}>
            Colophon · 발행 정보
          </p>
        </div>
        <h2 className="text-2xl font-black" style={{ color: THEME.textMain }}>
          Claude Magazine
        </h2>
        <p className="mt-1 text-sm" style={{ color: THEME.textSub }}>
          {issue} · {date}
        </p>
      </header>

      <hr className="mx-12 border-gray-100" />

      <main className="px-12 py-8 grid grid-cols-12 gap-6 text-sm">
        {/* 좌측: 발행 정보 */}
        <section className="col-span-5 space-y-4">
          <div>
            <p className={TYPE.category} style={{ color: THEME.primary }}>Publisher</p>
            <p className="mt-1 font-medium">{publisher}</p>
          </div>
          <div>
            <p className={TYPE.category} style={{ color: THEME.primary }}>Editor</p>
            <p className="mt-1 font-medium">{editor}</p>
          </div>
          <div>
            <p className={TYPE.category} style={{ color: THEME.primary }}>Contact</p>
            <p className="mt-1 font-medium">{email}</p>
          </div>
        </section>

        {/* 우측: 편집진 목록 */}
        <section className="col-span-7">
          <p className={TYPE.category} style={{ color: THEME.primary }}>Editorial Team</p>
          <ul className="mt-2 space-y-1.5">
            {team.map((member, idx) => (
              <li key={idx} className="flex justify-between">
                <span className="font-medium">{member.name}</span>
                <span className="text-xs" style={{ color: THEME.textSub }}>
                  {member.role}
                </span>
              </li>
            ))}
          </ul>

          {contributors.length > 0 && (
            <>
              <p className={`${TYPE.category} mt-4`} style={{ color: THEME.primary }}>
                Contributors
              </p>
              <p className="mt-1 text-xs" style={{ color: THEME.textSub }}>
                {contributors.join(" · ")}
              </p>
            </>
          )}
        </section>

        {/* AI 사용 고지 (전폭) */}
        <section
          className="col-span-12 mt-4 p-5 rounded-lg border-l-4"
          style={{
            backgroundColor: THEME.bgLight,
            borderLeftColor: THEME.accent,
          }}
        >
          <p className={TYPE.category} style={{ color: THEME.accent }}>
            AI Usage Notice · AI 사용 종합 고지
          </p>
          <p className="mt-2 text-xs leading-relaxed" style={{ color: THEME.textMain }}>
            {aiNotice}
          </p>
        </section>

        {/* 라이선스 + 정정 */}
        <section className="col-span-12 mt-2 space-y-2 text-xs" style={{ color: THEME.textSub }}>
          <p>{copyright}</p>
          <p>{corrections}</p>
        </section>
      </main>

      {/* 푸터 */}
      <footer
        className="px-12 py-4 flex justify-between items-center"
        style={{ backgroundColor: THEME.primary, color: "white" }}
      >
        <span className="text-xs font-black tracking-widest">CLAUDE MAGAZINE</span>
        <span className="text-xs font-light opacity-80">
          Powered by Anthropic · {date}
        </span>
      </footer>
    </div>
  );
};

export default ColophonPage;
