# TASK_046 — Figma 실구현 (무료 REST API, MCP 없이)

## 메타
- **status**: todo
- **prerequisites**: TASK_041 (slide JSON), TASK_042 (Figma 설계안 + plan builder)
- **예상 소요**: 120~150분
- **서브에이전트 분할**: 가능 (Phase 1 클라이언트 vs Phase 2 애플리케이터)
- **Phase**: 5 확장 후속 (SNS 자산 자동화)
- **Supersedes**: `tasks/TASK_046_draft.md` — 본 파일이 정식 사양

---

## 목적
TASK_042 `figma_card_news_sync.py`의 plan builder → **실제 Figma 프레임 생성**.
**무료 진행 원칙 엄수**:
- Figma **Free 플랜** + **Personal Access Token**만 사용 (Professional/Organization 과금 제거)
- **MCP 서버 미도입** — REST API 직접 호출 (외부 MCP 서버 의존성 제거)
- 유료 플러그인·Enterprise 기능 사용 금지

### 무료 범위 확인
| 항목 | 무료 가능 여부 |
|---|---|
| Personal Access Token 발급 | ✅ Figma Free 플랜 포함 |
| REST API 호출 (파일 읽기·쓰기) | ✅ 플랜 무관, 소유 파일만 |
| Personal drafts 파일 편집 | ✅ 무제한 |
| 팀 파일 공동작업 | ❌ 유료 — **본 태스크는 personal drafts만 대상** |
| Plugin 개발/배포 | ❌ 범위 외 |

---

## 구현 명세

### Phase 1: Figma REST 클라이언트 (50분)

#### 1.1 `pipeline/figma_client.py` (신규)
```python
# Figma REST API 최소 래퍼
# 엔드포인트:
#   GET    /v1/files/:file_key
#   POST   /v1/files/:file_key/nodes          (일부 API는 plugin 전용 — 회피)
#   PUT    /v1/files/:file_key/nodes/:id      (공개 REST에 부재 — 대안 필요)
```

**중요 기술 제약**: Figma REST API는 **읽기(GET)만 공개** — 노드 생성/수정은 Plugin API 또는 Dev Mode MCP가 필요.
**해결책**: 본 태스크는 **읽기 전용 + JSON 출력** 패턴으로 축소:

1. 편집자가 Figma Free 계정에 **빈 템플릿 파일** (1080×1350 FRAME 7개) 사전 준비
2. 본 파이프라인이 `slides.json` → **텍스트 붙여넣기용 Markdown 패키지** 생성
3. 편집자가 Figma 데스크톱 앱에서 해당 패키지의 텍스트를 수동 복사/Auto Layout 적용
4. 완료 후 REST API `GET /v1/files/:file_key/images` 호출로 이미지 export

→ 완전 자동 생성은 유료 Plugin/MCP 필요. 무료 경로에서는 **하이브리드(자동 템플릿 생성 지시 + 수동 채우기)**가 현실적.

#### 1.2 `pipeline/figma_client.py` 실제 기능
- `get_file_metadata(file_key)` — 파일 존재·권한 확인
- `export_frame_images(file_key, frame_node_ids, scale=2)` — 완성된 프레임 PNG export (유료 아님, REST 범위 내)
- `validate_token()` — 토큰 유효성 점검

### Phase 2: slide JSON → Figma 편집 지시서 생성기 (30분)

#### 2.1 `pipeline/figma_card_news_sync.py` 확장
기존 plan builder는 유지. 새 기능 추가:
- `generate_paste_package(slides_json, output_dir)` — 각 slide마다 .md 파일 생성
  - 파일명: `slide_01_hook.md` 등
  - 내용: 각 슬롯별 텍스트 + Figma Auto Layout 권장 constraint
  - 편집자가 Figma에서 슬라이드별로 복사/붙여넣기

#### 2.2 CLI 플래그 추가
- `--paste-package` : plan JSON + paste 패키지 동시 생성
- `--export-images <frame_ids.csv>` : 편집 완료된 프레임을 PNG로 export
- `--file-key`, `--access-token` (또는 env FIGMA_ACCESS_TOKEN)

### Phase 3: 무료 플랜 가드레일 (15분)

#### 3.1 토큰 유효성 + personal drafts 확인
```python
def ensure_free_plan_compatible(client, file_key):
    """파일이 사용자 personal drafts에 있고 편집 권한이 있는지 확인.
    팀 라이선스 필요 기능 사용 시 에러."""
```

- 파일 경로가 팀 워크스페이스면 **경고 로그** 출력 (실패 아님, 편집자 판단)
- 토큰이 조직 계정 토큰이면 **경고 로그**

#### 3.2 비용 측정
Figma REST API는 현재 완전 무료 (rate limit만 존재).
확인 대상:
- Rate limit: 분당 ~100~300 요청 (비공식). 월간 발행 규모(~100 호출)는 여유 있음
- `reports/task046_cost.md`에 기록 — **모든 런타임 비용 $0 명시**

### Phase 4: 편집자 워크플로우 문서 (20분)

#### 4.1 `docs/figma_workflow.md` (신규)
1. Figma Free 계정 생성 + Personal Access Token 발급 스크린샷 안내
2. 1080×1350 FRAME 7개 템플릿 파일 준비 방법
3. 본 파이프라인 실행 → paste package 생성 → Figma에 붙여넣기 흐름
4. 완성 후 이미지 export CLI 실행

#### 4.2 `.env.example` 주석 해제 (TASK_043에서 주석 처리한 Figma 섹션)
```
# Figma sync (TASK_046 — 무료 REST API)
FIGMA_FILE_KEY=your-figma-file-key
FIGMA_ACCESS_TOKEN=figd_...
```

### Phase 5: 스모크 + 회귀 (15분)
- TASK_041 샘플(reports/task041_smoke_1.json) 입력
- paste package 생성 확인 (5 slide → 5 md)
- plan JSON 출력 회귀 없음 (TASK_042 구조 유지)

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| Figma REST가 노드 쓰기 미지원 → 완전 자동화 불가 | Phase 2에서 하이브리드(자동 지시 + 수동 붙여넣기) 패턴으로 우회 |
| Rate limit 초과 | 월 발행 규모 대비 여유. 도달 시 지수 백오프 + 로깅 |
| 팀 라이선스 기능 실수 사용 | Phase 3.1 가드레일로 warning 로그 |
| 토큰 노출 | `.env`에만 보관, 로그 마스킹 (`figd_***`) |
| 향후 유료 MCP 도입 필요성 | 본 태스크에서 배우는 매핑 정보가 MCP 도입 시 재사용 가능 — 손실 없음 |
| 편집자 수동 단계 증가 | `docs/figma_workflow.md`로 표준화, 체크리스트 제공 |

---

## 완료 조건 (Definition of Done)
- [ ] `pipeline/figma_client.py` — REST 최소 래퍼 (read-only + image export만)
- [ ] `figma_card_news_sync.py --paste-package` 신규 플래그 동작
- [ ] `figma_card_news_sync.py --export-images` PNG export 동작
- [ ] Phase 3 가드레일: 팀 파일 감지 시 경고 로그
- [ ] `docs/figma_workflow.md` 편집자 가이드 작성
- [ ] `reports/task046_cost.md`에 **월 $0 명시** + rate limit 여유 계산
- [ ] `.env.example` Figma 섹션 주석 해제 + 무료 플랜 주석 추가
- [ ] 샘플 스모크 통과 (paste package 5 slide × 5 md 파일 생성)
- [ ] 기존 TASK_042 plan builder 회귀 없음
- [ ] Personal Access Token 노출 방지 (로그 마스킹)

---

## 산출물
- `pipeline/figma_client.py` (신규)
- `pipeline/figma_card_news_sync.py` (확장)
- `docs/figma_workflow.md` (신규)
- `reports/task046_cost.md` (신규)
- `.env.example` (주석 해제)

---

## 후속 태스크 후보
- **TASK_052 후보**: Figma Dev Mode MCP 활성화 (유료 플랜 도입 결정 시)
- **TASK_053 후보**: 완전 자동 노드 생성 (Figma Plugin 직접 개발 또는 Dev Mode 활용)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_046 implemented
python codex_workflow.py update TASK_046 merged
```
