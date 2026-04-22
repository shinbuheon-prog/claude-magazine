# TASK_037 — 월간 발행 원스톱 스크립트 + 대시보드 확장

## 메타
- **status**: todo
- **prerequisites**: TASK_035, TASK_036
- **예상 소요**: 70분
- **Phase**: 5 확장 (발행 자동화 완결)

## 목적
월간 발행을 **단일 스크립트**로 실행: 플랜 로드 → 품질 게이트 → PDF 컴파일 → Ghost 일괄 발행 → 뉴스레터 → SNS 재가공.
편집자 대시보드에는 **월간 진행률 위젯** 추가.

## 구현 명세

### 생성/수정 파일
```
scripts/
└── publish_monthly.py                  ← 원스톱 오케스트레이터

web/src/pages/
└── DashboardPage.jsx                   ← 월간 진행률 위젯 추가 (수정)
```

### publish_monthly.py CLI
```bash
# 전체 파이프라인 (dry-run 기본)
python scripts/publish_monthly.py --month 2026-05 --dry-run

# 실제 발행 (편집자 명시적 승인 플래그 필요)
python scripts/publish_monthly.py --month 2026-05 --publish --confirm

# 단계 스킵
python scripts/publish_monthly.py --month 2026-05 --skip-pdf
python scripts/publish_monthly.py --month 2026-05 --skip-sns
```

### 실행 단계 (각 단계 체크포인트·롤백 가능)
```
1. 플랜 로드 (plan_issue.status 호출)
   └─ 21꼭지 중 status=approved 여부 확인

2. 최종 품질 게이트 (각 꼭지)
   ├─ editorial_lint --strict
   ├─ standards_checker --category X
   └─ source_diversity --strict

3. AI 사용 고지 일괄 삽입 (disclosure_injector, heavy 템플릿)

4. PDF 컴파일 (compile_monthly_pdf.py 호출)

5. Ghost 일괄 발행 (ghost_client.create_post × 21 with status=published)

6. 뉴스레터 발송 (편집자 확인 후)

7. SNS 4채널 재가공 (channel_rewriter × 21 × 4 = 84회)

8. 아카이브 (drafts/ → archive/2026-05/)

9. 결과 리포트 (reports/publish_2026-05.md)
```

### 체크포인트 파일 (`reports/publish_state_YYYY-MM.json`)
```json
{
  "month": "2026-05",
  "stages": {
    "plan_loaded": true,
    "quality_gate": {"passed": 19, "failed": 2, "errors": [...]},
    "disclosure_injected": true,
    "pdf_compiled": "output/claude-magazine-2026-05.pdf",
    "ghost_published": [...],
    "newsletter_sent": false,
    "sns_distributed": {}
  }
}
```

각 단계 성공 시 상태 업데이트 → 중단 후 재실행 시 완료 단계는 스킵.

### DashboardPage.jsx 확장
기존 5개 카테고리 대시보드에 **월간 진행률 섹션** 추가:

```jsx
<section className="monthly-progress">
  <h2>2026-05 발행 진행률</h2>
  <div className="progress-bar">
    <div style={{width: '45%'}}>9.5% published</div>
  </div>

  <div className="status-grid">
    {['published', 'approved', 'lint', 'fact_check', 'draft', 'brief', 'planning'].map(
      s => <StatusCard status={s} count={counts[s]} />
    )}
  </div>

  <h3>꼭지 상세</h3>
  <table>
    {/* 21꼭지 목록: slug, category, status, assignee */}
  </table>
</section>
```

데이터 소스: `scripts/plan_issue.py status --month X --json` 호출 결과.

## 완료 조건
- [ ] `scripts/publish_monthly.py` 생성 (7단계 + 체크포인트)
- [ ] 각 단계 독립 실행 가능 (`--skip-*` 옵션)
- [ ] `--confirm` 플래그 없이는 published 전환 차단
- [ ] `DashboardPage.jsx`에 진행률 위젯 추가
- [ ] 스모크 테스트: `--dry-run`으로 단계 순서 검증

## 완료 처리
`python codex_workflow.py update TASK_037 merged`
