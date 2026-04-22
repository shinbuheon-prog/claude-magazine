# TASK_033 — Claude Agent SDK 통합 (Max 구독 경유, API 비용 0)

## 메타
- **status**: merged
- **prerequisites**: 없음
- **실 소요**: ~180분
- **서브에이전트 분할**: 불필요 (단독 구현)
- **Phase**: 5 확장 (인프라 비용 최적화)

---

## 목적
Anthropic API 직접 호출을 **Claude Agent SDK (Max 구독 경유)**로 교체.
월간 $15~$20 API 비용 → **$0 추가 비용** 달성 (Max $100 이미 지출).

리포트 인용: _"Max $100 구독 내 Sonnet·Opus·Haiku 전부 접근 가능. 월 350회 호출 = 한도의 약 20%."_

---

## 구현 결과

### 1. Provider 추상화 (`pipeline/claude_provider.py`)
3종 provider + factory:

```python
class Provider(ABC):
    def stream_complete(system, user, model_tier, max_tokens, stream_callback) -> CompleteResult

class AnthropicAPIProvider(Provider):    # 기존 경로 (pay-per-use)
class ClaudeAgentSDKProvider(Provider):   # Max 구독 경유, 추가 비용 0
class MockProvider(Provider):             # 테스트용
```

환경변수로 선택: `CLAUDE_PROVIDER=sdk|api|mock`

### 2. 리팩토링된 8개 모듈
| 모듈 | 모델 tier | 주요 호출 |
|---|---|---|
| brief_generator.py | sonnet | 기사 브리프 |
| draft_writer.py | sonnet | 본문 초안 |
| fact_checker.py | opus | 팩트체크 |
| channel_rewriter.py | haiku | SNS 재가공 |
| editorial_lint.py | sonnet | title-body-match |
| sop_updater.py | sonnet | 주간 개선 루프 |
| source_diversity.py | haiku | stance 분류 |
| source_ingester.py | haiku | RSS 분류 |

각 모듈 변경 패턴 (동일):
- `anthropic.Anthropic(api_key=...)` → `get_provider()`
- `client.messages.stream(model=...)` → `provider.stream_complete(tier=...)`
- `final.usage.input_tokens` → `result.input_tokens`

### 3. Windows 호환성 패치
`sys.stdout/stderr` 래핑이 다중 import 시 "I/O operation on closed file" 유발.
→ `_utf8_wrapped` 가드 도입 (`editorial_lint.py`, `fact_checker.py`):
```python
if sys.platform == "win32" and not getattr(sys.stdout, "_utf8_wrapped", False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stdout._utf8_wrapped = True
```

### 4. 하위 호환성
- `CLAUDE_PROVIDER=api` (기본값) → 기존 동작 100% 유지
- 기존 `test_e2e.py`의 `patch("anthropic.Anthropic", factory)` 그대로 동작 (동적 참조)
- 기존 API 키 인증 경로 폴백 가능

### 5. 검증 결과

**Step 1a — Sonnet 실호출 3회 연속 성공**:
- `ba3daa77-d833-4034-a3f4-70de83ef57e9` (Claude 4.6 테스트)
- `d79de791-bf0d-4ef7-a66e-d9228bb42eaa` (에이전트 프레임워크 비교)
- `8dadca0a-d5e9-4968-a1f6-7ebce7530d66` (한국 AI 기본법 대응)

**Step 1b — Opus 실호출 성공**:
- `3c9943cd-8075-4128-af37-dd16b1125303`
- 5개 문장 정밀 판정 + heuristics 주입 확인

**Step 2 검증** (`scripts/check_provider.py`):
- 9개 pipeline 모듈 import: **PASS**
- Mock 호출: **PASS**
- SDK Haiku 실호출: **PASS**
- 기존 E2E 테스트 (`test_e2e.py`): **14/0 PASS**

---

## 비용 효과

| 구성 | 월 고정비 | 추가 API | 품질 |
|---|---|---|---|
| **Before (API 직접)** | $0 | $15~$20 | 100% |
| **After (SDK + Max)** | $100 (이미 지출) | **$0** | 100% |

Max $100는 이미 쓰고 있던 구독 → **순 절감액 월 $15~$20** (연 $180~$240).

## 운영 전환

```bash
# 프로덕션 환경 설정
export CLAUDE_PROVIDER=sdk

# 이후 모든 파이프라인이 Max 구독 경유
python scripts/run_weekly_brief.py --topic "..."
python pipeline/fact_checker.py --draft ...

# 테스트 시
CLAUDE_PROVIDER=mock python scripts/test_e2e.py

# API 폴백 (키 설정된 경우)
CLAUDE_PROVIDER=api python pipeline/brief_generator.py --topic "..."
```

## 제약·유의사항
- Max 세션 5시간 자동 리셋 — 80페이지 일괄 작업 시 분할 필요
- Claude Code CLI 로그인 필수 — 서버 환경 배포 시 세션 토큰 관리
- SDK는 subprocess로 `claude` CLI 호출 → 동시성은 Max 한도 내 제한
- 개인 편집자·블로거 이용 OK, 상업 SaaS 재판매 금지

## 완료 후 처리
```bash
python codex_workflow.py update TASK_033 merged
```
