---
name: baoyu-article-illustrator
description: 기사 본문 섹션에 시각 보조 이미지를 삽입하는 래퍼 스킬. "기사 일러스트", "본문 시각화", "illustrate article" 요청에 사용.
allowed-tools: Bash, Read, Write
---

<!-- source: jimliu/baoyu-skills@8c17d77209b030a97d1746928ae348c99fefa775 -->

# Article Illustrator (Magazine Wrapper)

## 언제 사용
- 초안 본문에 섹션별 시각 자료 위치를 먼저 잡고 싶을 때
- `pipeline/draft_writer.py --illustrate` 경로로 prompt 파일과 이미지 placeholder 를 생성할 때
- 라이선스 로그와 request_id 연동을 준비해야 할 때

## 절차 (Systematic)

### 1. 초안 준비
- 먼저 `draft_writer.py` 로 섹션 초안을 만든다.
- 기사 id 또는 slug 를 정해 이미지 출력 경로를 고정한다.

### 2. 일러스트 훅 실행
```bash
python pipeline/draft_writer.py --brief drafts/sample_brief.json --section "인사이트" --out drafts/sample.md --dry-run --illustrate
```
- `pipeline/illustration_hook.py` 가 prompt 파일과 placeholder PNG, `logs/illustrations.jsonl` 을 만든다.
- 실제 baoyu 생성 백엔드 연결 전까지는 검토용 placeholder 로 동작한다.

### 3. 편집 검토
- 삽입된 `<img ... data-rights="placeholder-for-review" />` 태그 위치를 확인한다.
- 발행 전에는 실제 이미지 자산과 라이선스 값으로 교체한다.

## Verify before success
- [ ] `output/illustrations/<article_id>/` 아래 prompt 와 이미지가 생성됨
- [ ] 본문에 이미지 태그가 삽입됨
- [ ] `logs/illustrations.jsonl` 에 request_id, source, license 가 기록됨
- [ ] placeholder 상태면 발행 전 교체 필요가 명시됨
