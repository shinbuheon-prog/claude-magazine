# TASK_047 — 이미지 생성 backend 실구현 (무료 전용: Pollinations + HuggingFace)

## 메타
- **status**: todo
- **prerequisites**: TASK_043 (ABC IllustrationProvider + OpenAI 스켈레톤)
- **예상 소요**: 120~150분
- **서브에이전트 분할**: 가능 (Phase 1 Pollinations vs Phase 2 HuggingFace)
- **Phase**: 5 확장 후속 (내지 삽화 자동화)
- **Supersedes**: `tasks/TASK_047_draft.md` — 본 파일이 정식 사양

---

## 목적
TASK_043에서 OpenAI provider(유료)는 이미 스켈레톤이 들어가 있음. 본 태스크는 **무료 provider 2종을 추가**하고, **기본값을 무료 경로로 고정**해 무료 발행 원칙을 기술적으로 보증.

### 무료 제공자 후보 비교
| Provider | 인증 | Rate Limit | 품질 | 한국어 프롬프트 | 라이선스 |
|---|---|---|---|---|---|
| **Pollinations.ai** | 불필요 | 관대 (비공식, 수초/요청) | 중상 (Stable Diffusion·FLUX 기반) | 양호 | 무료 사용 허용 (상업적 가이드라인 존재) |
| **HuggingFace Inference API** | 무료 토큰 필요 | 시간당 제한 (warm model) | 중~고 | 모델 의존 | 모델별 — FLUX.1-schnell Apache-2.0 |
| OpenAI gpt-image-1 (기존 스켈레톤) | 필요 | — | 고 | 양호 | API 출력물 소유권 있음 — **유료** |
| Local Stable Diffusion | 불필요 | 없음 (로컬) | 모델 의존 | 양호 | 모델 라이선스 별도 (대부분 OpenRAIL) |

**선정 근거**:
- Pollinations — **인증 불필요 + 즉시 사용 가능** → 편집자 진입 장벽 0
- HuggingFace FLUX.1-schnell — Apache 2.0 라이선스 + 고품질, 상업적 사용 안전

**탈락**:
- Local Stable Diffusion: 편집자 GPU/VRAM 요구 너무 큼 (매거진 운영 단순성 해침)
- OpenAI gpt-image-1: 이미 TASK_043에 스켈레톤 존재, 본 태스크 범위 외

---

## 구현 명세

### Phase 1: Pollinations provider (35분)

#### 1.1 `pipeline/illustration_providers/pollinations.py` (신규)
```python
class PollinationsProvider(IllustrationProvider):
    name = "pollinations"
    requires_env: tuple[str, ...] = ()  # 인증 불필요

    # 엔드포인트: https://image.pollinations.ai/prompt/{url_encoded_prompt}
    # 파라미터 (query string):
    #   width, height, model (flux|sd|turbo), seed, nologo=true
    # 응답: image/jpeg 또는 image/png 바이트

    def generate(self, prompt, size, article_id, *, title, output_path, prompt_path=None):
        # url-encode prompt, GET with timeout 60s
        # 응답 바이트 저장, IllustrationResult 반환
        # license="pollinations-free-tier", cost_estimate=0.0
```

#### 1.2 라이선스·rate limit 가드
- 요청 간 최소 2초 간격 (`time.sleep`) — 서버 친화적 사용
- 실패 시 즉시 예외, 3회 지수 백오프 후 포기 → placeholder fallback
- user-agent 헤더에 `Claude-Magazine-KR/1.0` 명시 (투명성)

### Phase 2: HuggingFace Inference provider (35분)

#### 2.1 `pipeline/illustration_providers/huggingface.py` (신규)
```python
class HuggingFaceProvider(IllustrationProvider):
    name = "huggingface"
    requires_env = ("HUGGINGFACE_TOKEN",)

    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
    ENDPOINT = "https://api-inference.huggingface.co/models/{model}"

    def generate(self, prompt, size, article_id, *, title, output_path, prompt_path=None):
        # POST with json={"inputs": prompt, "parameters": {"width": w, "height": h}}
        # 응답: binary image bytes
        # 503 (model loading) 처리: 재시도 백오프
        # license 메타에 모델 정보 포함 — 사용 모델이 Apache 2.0인지 체크
```

#### 2.2 모델 라이선스 선택 가드
화이트리스트 모델 (Apache 2.0 / CC0 등 상업적 안전):
```python
SAFE_LICENSES = {
    "black-forest-labs/FLUX.1-schnell": "Apache-2.0",
    "stabilityai/stable-diffusion-xl-base-1.0": "CreativeML Open RAIL-M",
}
```
화이트리스트 외 모델 사용 시 명시적 에러 (안전망).

### Phase 3: fallback 체인 로직 (20분)

#### 3.1 `pipeline/illustration_hook.py` `_resolve_provider()` 확장
```python
FALLBACK_CHAIN = {
    "pollinations": ["pollinations", "placeholder"],
    "huggingface":  ["huggingface", "pollinations", "placeholder"],
    "openai":       ["openai", "placeholder"],
    "placeholder":  ["placeholder"],
}
```
- 첫 provider 실패 시 다음으로 자동 전환
- 모든 전환을 `logs/illustrations.jsonl`의 `provider_chain` 필드에 기록
- placeholder는 **항상 마지막**

#### 3.2 비용 상한 가드
env `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP` (기본값 `0.0` = 무료만)
- 0.0이면 cost_estimate > 0인 provider는 **자동 제외**
- 편집자가 명시적으로 $5.0 등 설정 시에만 유료 provider(openai) 활성화 가능
- 월 누적은 `data/illustration_cost_<YYYY-MM>.json`에 기록 (초기값 0.0)

### Phase 4: 스모크 + 회귀 (15분)

- Pollinations dry-run 실패 case mock (네트워크 차단 모사) → placeholder fallback 확인
- HuggingFace 토큰 없을 때 skip → fallback chain으로 pollinations·placeholder 이동 확인
- `CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER=pollinations` + 실제 호출 1건 (네트워크 의존 — dry-run 모드 별도 제공)
- placeholder 기본 경로 회귀 없음 (TASK_043 스모크 동일 결과)

### Phase 5: 문서화 (15분)

#### 5.1 `docs/illustration_backend_options.md` 업데이트
TASK_043에서 작성한 매트릭스에 **구현 상태** 컬럼 추가:
- Pollinations: **merged** (TASK_047)
- HuggingFace: **merged** (TASK_047)
- OpenAI: **skeleton only** (TASK_043)
- Placeholder: **merged** (TASK_040·043)

#### 5.2 `docs/illustration_workflow.md` (신규)
1. `CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER` 값별 동작 매트릭스
2. HuggingFace 토큰 발급 방법 (무료)
3. 월 $0 운영을 위한 권장 설정: `pollinations` (기본 변경 고려) 또는 `placeholder`
4. 품질 비교 예시 (같은 프롬프트 3 provider 결과 첨부 — 편집자 판단 보조)

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| Pollinations 서비스 중단 · 정책 변경 | fallback chain에 placeholder 항상 포함, 실패 시 무음 degrade |
| HuggingFace 무료 tier rate limit | 3회 재시도 후 pollinations·placeholder 순으로 fallback |
| 한국어 프롬프트 품질 저하 | 편집자 가이드에 영문 프롬프트 병행 권장 + 품질 비교 샘플 |
| 모델 라이선스 함정 (상업적 사용 불가 모델) | SAFE_LICENSES 화이트리스트 외 모델은 실행 차단 |
| 로컬 Stable Diffusion 유혹 | 도입 비권장 명시 — 편집자 PC 사양 가변성, 운영 복잡도 |
| 월 비용 상한 0.0이 의도 혼선 | env 기본값을 0.0으로 하고 OpenAI는 명시적 상향 필수 — 무료 발행 원칙 기술적 강제 |
| Pollinations 저작권 정책 변경 | `docs/illustration_workflow.md`에 발행 시점별 서비스 정책 확인 권장 |

---

## 완료 조건 (Definition of Done)
- [ ] `pipeline/illustration_providers/pollinations.py` 구현, 인증 없이 동작
- [ ] `pipeline/illustration_providers/huggingface.py` 구현, SAFE_LICENSES 가드
- [ ] `illustration_hook.py` fallback chain 확장, `provider_chain` 로그 필드 추가
- [ ] `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=0.0` 기본값 → 유료 provider 자동 제외
- [ ] `docs/illustration_backend_options.md` 구현 상태 컬럼 갱신
- [ ] `docs/illustration_workflow.md` 편집자 가이드 신규
- [ ] 스모크: 기본 placeholder 회귀 없음 + pollinations 실행 1건 성공 + fallback 동작 확인
- [ ] `logs/illustrations.jsonl`에 `provider`·`provider_chain`·`cost_estimate`·`license` 기록
- [ ] `reports/task047_cost.md`에 **기본 설정 월 $0 명시**
- [ ] mojibake/한국어 회귀 없음

---

## 산출물
- `pipeline/illustration_providers/pollinations.py` (신규)
- `pipeline/illustration_providers/huggingface.py` (신규)
- `pipeline/illustration_hook.py` (fallback chain 확장)
- `docs/illustration_backend_options.md` (업데이트)
- `docs/illustration_workflow.md` (신규)
- `reports/task047_cost.md` (신규)
- `.env.example` (주석 해제 + 무료 provider 강조)

---

## 후속 태스크 후보
- **TASK_054 후보**: 품질 비교 자동 리포트 (같은 프롬프트 N provider 비교표 자동 생성)
- **TASK_055 후보**: 로컬 FLUX schnell 실험 (GPU 있는 편집자용 옵션)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_047 implemented
python codex_workflow.py update TASK_047 merged
```
