# TASK_018 — AI 사용 고지 자동 삽입 (disclosure_injector.py)

## 메타
- **status**: todo
- **prerequisites**: TASK_002
- **예상 소요**: 20분
- **서브에이전트 분할**: 불필요
- **Phase**: 3 (투명성·저작권)

---

## 목적
모든 발행 기사 하단에 **AI 사용 고지 문구**를 자동 삽입.
리포트 인용: _"AI 출력 책임은 반드시 사람에게 귀속. 기사 하단에 AI 보조 생성/분석 사용 고지."_

---

## 구현 명세

### 생성할 파일: `pipeline/disclosure_injector.py`

### CLI
```bash
# HTML 파일에 고지 삽입
python pipeline/disclosure_injector.py --html article.html --output article_disclosed.html

# 템플릿 지정
python pipeline/disclosure_injector.py --html article.html --template heavy

# Ghost 포스트 ID로 삽입 (기존 포스트 업데이트)
python pipeline/disclosure_injector.py --ghost-post-id POST_ID
```

### 고지 템플릿 3종

**light (기본)** — 단순 기사용
```html
<div class="ai-disclosure" data-version="1.0">
  <p>이 기사는 Claude AI 보조 도구를 사용해 작성되었습니다.
     최종 편집 책임은 Claude Magazine 편집팀에 있습니다.</p>
  <p>정정 요청: editorial@claude-magazine.kr (24시간 내 1차 응답)</p>
</div>
```

**heavy** — 팩트체크·데이터 분석 심층 리포트용
```html
<div class="ai-disclosure" data-version="1.0">
  <h4>AI 사용 고지</h4>
  <ul>
    <li>브리프·초안 작성: claude-sonnet-4-6</li>
    <li>팩트체크: claude-opus-4-7</li>
    <li>데이터 분석: {{used_models}}</li>
  </ul>
  <p>모든 수치·인용은 편집자가 원문과 대조 검증했습니다.
     출처는 각 문장 말미의 [src-xxx] 참조.</p>
  <p>정정 요청: editorial@claude-magazine.kr (24시간 내 1차 응답)</p>
</div>
```

**interview** — 인터뷰 기사용
```html
<div class="ai-disclosure" data-version="1.0">
  <p>본 인터뷰는 편집팀이 직접 진행했으며,
     녹취 정리·초안 구성에 Claude AI 보조 도구를 사용했습니다.</p>
  <p>인터뷰이 발언은 AI 생성이 아닌 원문 녹취 기반입니다.</p>
  <p>정정 요청: editorial@claude-magazine.kr (24시간 내 1차 응답)</p>
</div>
```

### 함수 시그니처
```python
def inject_disclosure(
    html: str,
    template: str = "light",
    used_models: list[str] | None = None,
) -> str:
    """기존 HTML 하단에 고지 삽입, 중복 삽입 방지 (data-version 확인)"""

def get_template(name: str) -> str:
    """템플릿 조회 — light | heavy | interview"""

def update_ghost_post(post_id: str, template: str = "light") -> dict:
    """
    Ghost API로 포스트 HTML fetch → 고지 삽입 → PUT 업데이트
    반환: {post_id, updated_at, disclosure_version}
    """
```

### 중복 삽입 방지
- `<div class="ai-disclosure" data-version="X.Y">` 존재 여부 검사
- 이미 있으면: 기존 제거 → 새 버전 삽입
- 이렇게 하면 템플릿 변경 시 전체 기사에 재적용 가능

### CSS (web/src/index.css에 추가할 스니펫)
```css
.ai-disclosure {
  margin-top: 3rem;
  padding: 1rem 1.5rem;
  background: #F8F7F4;
  border-left: 3px solid #C96442;
  font-size: 0.85rem;
  color: #6B7280;
}
.ai-disclosure h4 { font-size: 0.9rem; margin-bottom: 0.5rem; color: #1B1F3B; }
.ai-disclosure ul { margin: 0.5rem 0; padding-left: 1.25rem; }
```

### 출력 형식
```
=== AI 사용 고지 삽입 ===
입력: article.html
템플릿: heavy
사용 모델: claude-sonnet-4-6, claude-opus-4-7

✅ 기존 고지 v1.0 발견 — 제거 후 v1.0 재삽입
✅ 출력 저장: article_disclosed.html (+487 bytes)
```

---

## 완료 조건
- [ ] `pipeline/disclosure_injector.py` 생성
- [ ] 3개 템플릿 (light / heavy / interview) 구현
- [ ] `inject_disclosure`, `get_template`, `update_ghost_post` 구현
- [ ] 중복 삽입 방지 (기존 data-version 감지 후 교체)
- [ ] `web/src/index.css`에 CSS 스니펫 추가
- [ ] 스모크 테스트: HTML 입력 → 고지 삽입 → 중복 방지 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_018 implemented
```
