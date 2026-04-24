# TASK_042 — Figma MCP 옵션 조사 + slide JSON → Figma 노드 통합 설계안

## 메타
- **status**: todo
- **prerequisites**: TASK_041 (slide JSON 스키마), TASK_039 (MCP frontmatter 대기 중)
- **예상 소요**: 90~120분
- **태스크 유형**: **조사·설계 (구현 아님)**
- **서브에이전트 분할**: 불필요
- **Phase**: 5 확장 후속 (외부 연동 설계)

---

## 목적
TASK_041에서 생성된 카드뉴스 slide JSON을 Figma 프레임으로 자동 전개하기 위한 **통합 설계안 문서화**.
본 태스크는 **실구현이 아닌 조사·비교·설계 문서 작성**이 범위.
Figma MCP 서버 구현 및 실제 연동은 후속 태스크(TASK_044 후보)로 분리.

---

## 조사 범위

### 1. Figma MCP 서버 후보 비교 (최소 3개)
다음 관점으로 후보 서버를 비교:
- 공식 Figma MCP (있다면)
- 커뮤니티 MCP 서버 (GitHub 검색)
- Figma REST API 직접 래퍼

**비교 매트릭스**:
| 후보 | 라이선스 | 유지보수 | 지원 기능(read/write/style) | 인증 방식 | 의존성 |
|---|---|---|---|---|---|
| 후보 A | | | | | |
| 후보 B | | | | | |
| 후보 C | | | | | |

### 2. slide JSON → Figma 노드 매핑
TASK_041 스키마:
```json
{
  "channel": "sns",
  "format": "card-news",
  "slides": [
    {
      "idx": 1, "role": "hook", "layout": "layout_6",
      "tag": "...", "main_copy": "...", "sub_copy": "...",
      "highlight": "...", "footer": "..."
    }
  ]
}
```

각 필드가 Figma 어떤 노드로 매핑되는지 설계:
- slide → FRAME (1080×1350)
- tag → TEXT 노드 + 배경 SHAPE
- main_copy / sub_copy / highlight → TEXT 노드 (웨이트·사이즈 구분)
- footer → TEXT 노드 + 화살표 ICON
- 7 layout 패턴 각각의 컴포넌트 인스턴스 배치

### 3. 인증·권한 설계
- 토큰 저장 위치 (`.env` 키명 제안)
- 팀 파일 권한 최소 범위
- 실패 시 fallback (read-only 모드, 토큰 회전 정책)

### 4. 통합 지점 (코드 없음, 설계만)
- `pipeline/channel_rewriter.py` 출력 후 어디에 Figma 호출을 끼울지
- 비동기·배치·에러 처리 전략
- `logs/card_news.jsonl`에 Figma 파일 URL 기록 확장안

---

## 산출물 (구현 파일 없음, 문서 중심)

### 1. `docs/figma_integration_plan.md` (신규, 필수)
섹션 구성:
1. **MCP 서버 후보 비교 매트릭스** (최소 3개)
2. **권장안 + 선정 근거** (1개 권장, 탈락 사유 명시)
3. **slide JSON → Figma 노드 매핑표**
4. **7 layout 패턴별 컴포넌트 설계** (텍스트·이미지·아이콘 배치 좌표)
5. **인증·권한·실패 처리**
6. **파이프라인 통합 지점** (channel_rewriter 이후 어디에)
7. **후속 태스크 후보** (TASK_044 Figma 실구현 범위 제안)
8. **리스크 및 미해결 질문**

### 2. `docs/figma_mcp_comparison.md` (신규, 선택)
MCP 서버 후보별 상세 비교. 조사량이 많으면 별도 문서로 분리, 적으면 `figma_integration_plan.md` §1에 통합.

### 3. `tasks/TASK_044_draft.md` (신규, 선택)
설계안 기반으로 후속 실구현 태스크 초안 스케치 (status: draft).

---

## 조사 제약 조건
- **무료 발행 원칙 유지**: Figma 유료 플랜 의존 기능은 권장안에서 제외 (Free/Professional 기본 기능 우선)
- **한국어 텍스트 필수**: slide의 한글 텍스트가 Figma에서 깨지지 않는 폰트 로딩 전략 포함
- **TASK_041 스키마 준수**: slide JSON 필드 이름 임의 변경 금지 (Figma 매핑만 추가)

---

## 탈락시킬 옵션 (명시적 제외)
다음은 조사에서 **제외**하거나 리스크 섹션에 명시:
- 유료 플러그인 의존 (Figma Tokens Studio 등 상업 확장)
- 리버스엔지니어링 기반 비공식 API (TASK_025 Pass/Fail 스펙 충돌)
- Figma Cloud 외부 서비스(클라우드 랜더러 등) — 라이선스·데이터 이동 리스크

---

## 완료 조건 (Definition of Done)
- [ ] `docs/figma_integration_plan.md` 작성, 8 섹션 모두 채워짐
- [ ] MCP 서버 후보 최소 3개 비교 (라이선스 명시, GitHub URL 포함)
- [ ] 권장안 1개 선정, 선정 근거 2문장 이상
- [ ] slide JSON 모든 필드의 Figma 노드 매핑 테이블 완성
- [ ] 7 layout 패턴 중 최소 3개 패턴에 대한 컴포넌트 배치 설계 포함
- [ ] 인증 방식 + `.env` 키명 제안
- [ ] 탈락 옵션 섹션에 유료·리버스엔지니어링·외부 서비스 명시
- [ ] 후속 실구현 태스크(TASK_044) 범위 1~2 단락 스케치

---

## 후속 태스크 (본 태스크 범위 외)
- **TASK_044 후보**: 본 설계안 기반 Figma MCP 실구현 — 토큰 설정·노드 생성·배치 자동화
- **TASK_039 잔여 활성화**: MCP 서버가 구현되면 SKILL.md `mcpServers` frontmatter 활성화

---

## 완료 처리
```bash
python codex_workflow.py update TASK_042 implemented   # 문서 작성 완료 후
python codex_workflow.py update TASK_042 merged        # 검토 완료 후
```
