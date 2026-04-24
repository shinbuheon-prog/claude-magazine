# TASK_044 — Prompt Caching 도입 (fact_checker · editorial_lint · brief_generator)

## 메타
- **status**: todo
- **prerequisites**: TASK_003 (brief_generator), TASK_005 (fact_checker), TASK_016 (editorial_lint), TASK_033 (claude_provider 추상화)
- **예상 소요**: 90분
- **서브에이전트 분할**: 불필요
- **Phase**: 5 확장 (API 효율화)

---

## 목적
[anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) **Prompt Caching** 레시피 도입.
매거진은 동일 system prompt (편집 10 체크 규칙·팩트체크 기준·브리프 템플릿)를 **매 호출마다 재전송**. 캐시 적용 시 system prompt 부분이 재사용되어 **비용 최대 90% 절감 + 레이턴시 감소**.

**적용 후보 (큰 순)**:
1. `fact_checker.py` — Opus 4.7, 판정 기준 + 출처 번들 system prompt 반복
2. `editorial_lint.py` — 10 체크 규칙 반복
3. `brief_generator.py` — template_A_brief.txt 반복
4. `draft_writer.py` — template_B_draft.txt 반복

---

## 중요 전제 (Phase 0에서 반드시 확인)

**TASK_033에서 Agent SDK(Max 구독) 경로 = API 비용 0**으로 전환됨. Prompt Caching은 **API 직접 호출 경로에서만 동작**.
따라서:

1. **CLAUDE_PROVIDER=sdk 경로**: Max 구독 이미 비용 0 → 캐싱 불필요
2. **CLAUDE_PROVIDER=api 경로**: 캐싱 적용 실익 有 → 본 태스크 주 대상

[pipeline/claude_provider.py](../pipeline/claude_provider.py)에 provider별 분기 존재. 캐싱 코드는 **api provider 내부에만** 추가. SDK provider는 건드리지 않음.

---

## 구현 명세

### Phase 0: 적용 범위 확정 (15분)
- 현재 `CLAUDE_PROVIDER` 기본값이 `api`임을 확인
- 각 파이프라인이 system prompt로 전달하는 텍스트 크기 측정
  - `fact_checker.py`: 판정 기준 + 출처 번들 — 대략 몇 토큰?
  - `editorial_lint.py`: 10 체크 설명 — 대략 몇 토큰?
- **1024 토큰 이상**이어야 캐싱 실익 있음 (Anthropic 권장 최소). 미달 시 해당 파이프라인은 스킵
- 결과를 `reports/task044_cache_scope.md`에 기록

### Phase 1: claude_provider.py 캐싱 옵션 추가 (20분)
- `AnthropicAPIProvider`에 `cache_system: bool = False` 파라미터 추가
- `cache_system=True`일 때 `system` 블록에 `cache_control: {"type": "ephemeral"}` 추가
- SDK/Mock provider는 **무시 파라미터로 통과** (회귀 없음)
- 사용 예:
  ```python
  provider.messages_stream(
      model="opus",
      system=[{"type": "text", "text": STATIC_RULES, "cache_control": {"type": "ephemeral"}}],
      messages=[...],
      cache_system=True,
  )
  ```
- `claude_provider.py`에 단위 테스트 블록 (`if __name__ == "__main__":`) 추가

### Phase 2: fact_checker.py 적용 (20분)
- **캐시 대상**: 판정 기준 규칙 (static) + 출처 번들 구조 설명 (semi-static)
- **캐시 비대상**: `<draft>{{draft_text}}</draft>` (매번 다름)
- system prompt를 `[규칙 블록 (캐시)] + [출처 번들 (캐시)]`의 2-블록 구조로 재편
- `cache_control` 는 마지막 캐시 대상 블록에만 부착 (누적 캐싱 패턴)
- 기존 Opus 4.7 모델 유지 (CLAUDE.md 모델 배치 규칙)
- `logs/`에 request_id 외 **cache_creation_input_tokens**, **cache_read_input_tokens** 기록

### Phase 3: editorial_lint.py 적용 (15분)
- 10 체크 규칙 설명을 static 블록으로 분리 → 캐시 대상
- 기사별 가변 부분(draft 본문)은 user message
- Haiku 모델은 캐싱 지원 확인 (cookbook 레시피 참조)

### Phase 4: brief_generator.py 적용 (선택, 10분)
- `prompts/template_A_brief.txt` (1203 bytes ≈ 300~500 토큰) — **1024 토큰 미만 가능성**
- Phase 0 측정 결과 1024 이상일 때만 적용, 아니면 skip하고 이유 기록

### Phase 5: 스모크 + 캐시 히트 검증 (10분)
- 같은 기사 2회 연속 `fact_checker` 실행
- `logs/*.jsonl`에서 cache_read_input_tokens > 0 확인
- 두 번째 호출이 첫 번째보다 **usage.input_tokens 감소 + 레이턴시 감소** 확인
- 결과를 `reports/task044_cache_smoke_<date>.md`에 기록

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| Max 구독 SDK 경로에 캐싱 코드 주입해 불필요한 토큰 구조 변경 | Phase 1에서 api provider 내부에만 분기, SDK는 무시 |
| 1024 토큰 미달 파이프라인에 캐싱 적용해 오히려 오버헤드 | Phase 0 측정으로 사전 차단 |
| 출처 번들이 매번 달라지면 캐시 미스 | 출처 번들은 기사 단위로 가변 — "semi-static" 표시, 같은 기사 내 여러 호출 시에만 캐시 히트. 기대치 조정 |
| cache_control 블록 순서 변경 시 캐시 무효화 | cookbook 권장 순서(정적 → 가변) 준수, 주석으로 순서 고정 명시 |
| Claude 모델 업그레이드 시 캐시 헤더 스펙 변경 | `claude_provider.py` 중앙 집중 → 교체 1 지점에서 처리 가능 |

---

## 무료 발행 원칙 정합성
- Max 구독 SDK 경로는 비용 0 유지 (본 태스크 영향 없음)
- API 경로에서만 캐싱 적용 → **비용 증가 없이 감소만 발생**
- 캐시 자체는 Anthropic 인프라 — 매거진 측 추가 비용 0

---

## 완료 조건 (Definition of Done)
- [ ] Phase 0: 4개 파이프라인 system prompt 토큰 측정 리포트 작성 (`reports/task044_cache_scope.md`)
- [ ] `claude_provider.py`에 `cache_system` 옵션 추가, SDK/Mock 회귀 없음
- [ ] `fact_checker.py` 캐싱 적용, 2-블록 구조로 재편
- [ ] `editorial_lint.py` 캐싱 적용 (1024 토큰 초과 시)
- [ ] `brief_generator.py`·`draft_writer.py`는 측정 결과에 따라 적용 또는 skip (스킵 시 이유 기록)
- [ ] `logs/*.jsonl`에 cache_creation_input_tokens·cache_read_input_tokens 기록
- [ ] 스모크 테스트: 같은 기사 2회 실행 시 두 번째 호출 input 토큰 **50% 이상 감소** 확인
- [ ] `reports/task044_cache_smoke_<date>.md` 작성 (before/after 토큰 비교 + 레이턴시)
- [ ] CLAUDE.md 코딩 규칙 준수 (request_id 로깅, 환경변수 직접 읽기, dry-run 옵션 유지)

---

## 산출물
- `pipeline/claude_provider.py` (확장, cache_system 파라미터)
- `pipeline/fact_checker.py` (2-블록 system prompt 재편)
- `pipeline/editorial_lint.py` (캐싱 적용)
- `pipeline/brief_generator.py` (조건부 적용)
- `reports/task044_cache_scope.md` (신규)
- `reports/task044_cache_smoke_<date>.md` (신규)

---

## 후속 태스크 후보
- **TASK_046 후보**: cache 히트율 모니터링 위젯 — TASK_028 운영 투명성 대시보드 확장

---

## 완료 처리
```bash
python codex_workflow.py update TASK_044 implemented
python codex_workflow.py update TASK_044 merged
```
