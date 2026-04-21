# TASK_006 — 주간 브리프 발행 스크립트

## 메타
- **status**: todo
- **prerequisites**: TASK_002, TASK_003
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요

---

## 목적
`scripts/run_weekly_brief.py`를 완성해
브리프 생성 → 초안 생성 → Ghost 임시저장/발행 전체 흐름을 한 커맨드로 실행한다.

---

## 구현 명세

### 파일: `scripts/run_weekly_brief.py` (기존 파일 검토 후 완성)

### 실행 흐름
```
1. brief_generator.generate_brief(topic, source_bundle)
   → drafts/brief_TIMESTAMP.json 저장

2. draft_writer.write_section(brief, section_name) × outline 전체 섹션
   → drafts/draft_TIMESTAMP.md 저장

3. ghost_client.create_post(title, html, status)
   → dry-run: status="draft"
   → publish: status="published" 후 send_newsletter()

4. logs/publish_TIMESTAMP.json 저장
   {timestamp, topic, ghost_post_id, ghost_url, mode: "dry-run"|"publish"}
```

### CLI 인터페이스 (반드시 이 형태)
```bash
# 드라이런: 브리프+초안+Ghost draft까지만 (발송 안 함)
python scripts/run_weekly_brief.py --topic "TOPIC" --dry-run

# 실제 발행
python scripts/run_weekly_brief.py --topic "TOPIC" --publish

# 소스 파일 지정
python scripts/run_weekly_brief.py --topic "TOPIC" --sources src1.md src2.md --dry-run
```

### 출력 (실행 중 콘솔)
```
=== 주간 브리프 시작: TOPIC ===
[1/3] 브리프 생성 중...
  제목 후보: ...
  브리프 저장: drafts/brief_20260421_120000.json
[2/3] 초안 생성 중...
  섹션: 서론
  섹션: 본론
  초안 저장: drafts/draft_20260421_120000.md
[3/3] Ghost 게시 중...
  결과: {post_id: ..., url: ..., status: draft}
=== 완료 (dry-run) ===
```

---

## 완료 조건
- [ ] `--dry-run` 실행 시 Ghost에 draft 포스트 생성 확인
- [ ] `--publish` 실행 시 Ghost에 published 포스트 생성 확인
- [ ] `logs/publish_TIMESTAMP.json` 생성 확인
- [ ] `--sources` 없이 실행해도 오류 없음 (소스 없음 메시지 출력)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_006 implemented
```
