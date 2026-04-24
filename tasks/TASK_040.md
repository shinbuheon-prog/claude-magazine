# TASK_040 — baoyu-skills High 시너지 4종 선별 도입

## 메타
- **status**: todo
- **prerequisites**: TASK_021 (CoverPage 일러스트 드롭인), TASK_030 (.claude/skills/), TASK_032 (source_ingester.py), TASK_009 (InsightPage)
- **예상 소요**: 120~180분
- **서브에이전트 분할**: 가능 (4 스킬별 Codex 병렬 위임)
- **Phase**: 5 확장 (외부 스킬 선별 도입)

---

## 목적
[jimliu/baoyu-skills](https://github.com/jimliu/baoyu-skills) 18종 중 **매거진 공백 영역을 정확히 메우는 4종만 선별 도입**.
완전 통합이 아닌 **레퍼런스 후 필요 요소만 포팅** — TASK_038(typeui.sh) 동일 원칙.

편집자 흐름 변화:
- **소스 수집**: RSS/Atom 전용 → +임의 웹페이지 + YouTube 자막
- **내지 삽화**: 커버만 존재 → 본문 삽화 자동 생성
- **인사이트 시각화**: Recharts 숫자 차트 → +21 레이아웃 인포그래픽

---

## 도입 대상 4종

| baoyu 스킬 | 매거진 공백 | 통합 지점 |
|---|---|---|
| `baoyu-url-to-markdown` | `source_ingester.py`가 RSS/Atom 전용 — JS 렌더링 페이지 수집 불가 | [pipeline/source_ingester.py](../pipeline/source_ingester.py) 확장 |
| `baoyu-youtube-transcript` | 영상 원본 자료 수집 수단 없음 | [config/feeds.yml](../config/feeds.yml) + source_ingester 신규 entry type |
| `baoyu-article-illustrator` | [web/src/components/](../web/src/components/) 커버만 존재, 내지 삽화 공백 | [pipeline/draft_writer.py](../pipeline/draft_writer.py) 후단 훅 |
| `baoyu-infographic` | InsightPage 숫자 차트만, 21 레이아웃 인포그래픽 부재 | [web/src/components/InsightPage.jsx](../web/src/components/InsightPage.jsx) 보강 |

---

## 도입 제외 14종 (참고)
- **중국 플랫폼**: `baoyu-post-to-wechat`, `baoyu-post-to-weibo`, `baoyu-xhs-images` — 한국 타깃 불일치
- **중복**: `baoyu-post-to-x`(channel_rewriter.py), `baoyu-cover-image`(TASK_021), `baoyu-markdown-to-html`(ghost_client.py)
- **톤앤매너 불일치**: `baoyu-comic`, `baoyu-slide-deck`
- **리스크**: `baoyu-danger-gemini-web`, `baoyu-danger-x-to-markdown` — 비공식 API 리버스엔지니어링, TASK_025 Pass/Fail 스펙과 충돌
- **불필요**: `baoyu-compress-image`(Puppeteer 파이프라인에 sharp 여지), `baoyu-format-markdown`(editorial_lint.py 중복), `baoyu-diagram`·`baoyu-imagine`(Medium 시너지, 별도 태스크 후보)

---

## 구현 명세

### Phase 1: 선별 설치 + 한국어 회귀 테스트 (60분)

#### 1.1 스킬 pull (일괄 설치 금지)
```bash
# npx skills add jimliu/baoyu-skills 전체 설치 금지 — 네임스페이스 오염 방지
# 개별 clone 후 필요한 것만 .claude/skills/baoyu-*/로 복제
git clone --depth 1 https://github.com/jimliu/baoyu-skills /tmp/baoyu-skills
cp -r /tmp/baoyu-skills/skills/baoyu-url-to-markdown      .claude/skills/
cp -r /tmp/baoyu-skills/skills/baoyu-youtube-transcript   .claude/skills/
cp -r /tmp/baoyu-skills/skills/baoyu-article-illustrator  .claude/skills/
cp -r /tmp/baoyu-skills/skills/baoyu-infographic          .claude/skills/
```

#### 1.2 라이선스 확인
- `LICENSE` 파일이 MIT/Apache-2.0 인지 검증
- 각 SKILL.md 상단에 `source: jimliu/baoyu-skills@<commit-sha>` 주석 추가

#### 1.3 한국어 회귀 테스트 (필수)
중국어 프롬프트 기반일 가능성 — 한국어 출력 품질 확인.
```bash
python scripts/validate_skills.py --skill baoyu-url-to-markdown --lang ko
```
- 테스트 케이스: 한국어 매거진 소스 3개 (예: 카카오 테크블로그·Naver D2·LINE Engineering)
- **실패 조건**: 출력에 중국어 간체자 혼입, frontmatter 필드명 중국어
- **조치**: SKILL.md 프롬프트 한국어 어댑터 레이어 추가 (원본 수정 금지, wrapper 작성)

#### 1.4 산출물
- `.claude/skills/baoyu-url-to-markdown/SKILL.md` (한국어 어댑터 포함)
- `.claude/skills/baoyu-youtube-transcript/SKILL.md`
- `.claude/skills/baoyu-article-illustrator/SKILL.md`
- `.claude/skills/baoyu-infographic/SKILL.md`
- `docs/baoyu_skills_audit.md` — 라이선스·변경 내역·회귀 테스트 결과

---

### Phase 2: source_ingester 확장 — URL·YouTube 인입 (40분)

#### 2.1 config/feeds.yml 스키마 확장
```yaml
feeds:
  - type: rss
    url: https://example.com/feed
  # 신규 type
  - type: url
    url: https://example.com/article         # 단일 웹페이지
    skill: baoyu-url-to-markdown
  - type: youtube
    url: https://youtube.com/watch?v=XXX
    skill: baoyu-youtube-transcript
```

#### 2.2 pipeline/source_ingester.py
- `ingest_url(url: str) -> SourceEntry` 함수 추가 — skill 호출 → markdown → source_registry 등록
- `ingest_youtube(url: str) -> SourceEntry` 함수 추가 — transcript + cover image 추출
- 기존 RSS 경로는 변경 없음 (회귀 방지)

#### 2.3 테스트
`if __name__ == "__main__":` 블록에 스모크 테스트 추가 — 각 type 1건씩 dry-run.

---

### Phase 3: draft_writer 후단 삽화 훅 (40분)

#### 3.1 pipeline/draft_writer.py
섹션 초안 생성 후 `--illustrate` 플래그로 baoyu-article-illustrator 호출.
```python
# draft 완료 후
if args.illustrate:
    from pipeline.illustration_hook import inject_illustrations
    draft_md = inject_illustrations(draft_md, skill="baoyu-article-illustrator")
```

#### 3.2 pipeline/illustration_hook.py (신규)
- Skill 호출 결과를 markdown `![alt](path)` 형태로 본문 삽입
- 이미지 저장: `output/illustrations/<article_id>/NN.png`
- 라이선스 태그: `logs/illustrations.jsonl` 에 source=skill·model·request_id 기록 (TASK_008 Langfuse 관측 연동)

#### 3.3 편집 체크리스트 7번 연동
CLAUDE.md "이미지·표·차트 라이선스 기록 완료" → illustration_hook가 자동 충족.

---

### Phase 4: InsightPage 인포그래픽 확장 (30분)

#### 4.1 web/src/components/InsightPage.jsx
- baoyu-infographic 21 레이아웃 중 **3종만 채택**: `comparison`, `timeline`, `process-flow`
- 기존 Recharts 기반 숫자 차트는 유지 — 공존
- 신규 prop: `<InsightPage layout="comparison" data={...} />`

#### 4.2 스킬 호출 지점
편집자가 월간 플랜 작성 시 `plan_issue.py --infographic <layout>` 로 SVG 생성 → React component에 import.

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| 중국어 프롬프트 혼입 | Phase 1.3 한국어 회귀 테스트 필수 통과 |
| 외부 스킬 버전 드리프트 | SKILL.md 상단에 commit SHA 고정 (`source: jimliu/baoyu-skills@<sha>`) |
| 네임스페이스 오염 | 4개만 개별 clone, `npx skills add` 일괄 설치 금지 |
| 이미지 생성 비용 | baoyu-article-illustrator 기본 provider 확인 — 무료 발행 원칙상 API 비용 통제 필수 |
| TOS 리스크 | baoyu-danger-* 스킬은 **절대 도입 금지** (본 태스크 도입 제외 목록 참조) |

---

## 완료 조건 (Definition of Done)
- [ ] 4 스킬이 `.claude/skills/baoyu-*/`에 설치되고 `docs/baoyu_skills_audit.md`에 라이선스·SHA 기록
- [ ] 한국어 회귀 테스트 3 케이스 통과 (각 스킬당 1건 이상)
- [ ] `source_ingester.py`가 `type: url` / `type: youtube` 처리, 기존 RSS 회귀 없음
- [ ] `draft_writer.py --illustrate` 플래그로 본문 삽화 삽입 동작
- [ ] `InsightPage.jsx`에 3 레이아웃(`comparison`·`timeline`·`process-flow`) 렌더링 확인
- [ ] `logs/illustrations.jsonl`에 request_id + license 기록 (CLAUDE.md 코딩 규칙 준수)
- [ ] 월간 PDF 빌드 회귀 없음 (`scripts/build_and_pdf.ps1` 통과)

---

## 산출물
- `.claude/skills/baoyu-url-to-markdown/` (한국어 어댑터 포함)
- `.claude/skills/baoyu-youtube-transcript/`
- `.claude/skills/baoyu-article-illustrator/`
- `.claude/skills/baoyu-infographic/`
- `pipeline/source_ingester.py` (확장)
- `pipeline/illustration_hook.py` (신규)
- `pipeline/draft_writer.py` (`--illustrate` 플래그)
- `web/src/components/InsightPage.jsx` (layout prop 확장)
- `config/feeds.yml` (type=url/youtube 스키마 확장)
- `docs/baoyu_skills_audit.md` (신규)
- `scripts/validate_skills.py` (한국어 회귀 테스트 추가)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_040 implemented   # Codex 구현 후
python codex_workflow.py update TASK_040 merged        # Claude Code 최종 머지 후
```
