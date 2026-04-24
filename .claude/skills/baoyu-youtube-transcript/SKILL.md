---
name: baoyu-youtube-transcript
description: YouTube 링크에서 자막·썸네일 메타데이터를 매거진 수집 경로로 연결하는 래퍼 스킬. "유튜브 자막", "YouTube transcript", "영상 출처 수집" 요청에 사용.
allowed-tools: Bash, Read, Write
---

<!-- source: jimliu/baoyu-skills@8c17d77209b030a97d1746928ae348c99fefa775 -->

# YouTube Transcript (Magazine Wrapper)

## 언제 사용
- 기사 소스에 유튜브 영상 원문이나 썸네일 메타데이터를 연결할 때
- `config/feeds.yml` 에 `type: youtube` 엔트리를 추가할 때
- 실제 자막 추출 전, 매거진 플래닝 단계에서 영상 소스 슬롯을 먼저 만들 때

## 절차 (Systematic)

### 1. 영상 식별
- YouTube URL 또는 video id 에서 11자리 video id 를 확인한다.
- 언어와 예상 토픽을 `feeds.yml` 에 함께 기록한다.

### 2. 래퍼 수집 실행
```bash
python scripts/run_source_ingest.py --feeds-config config/feeds.yml --dry-run
```
- 프로젝트 wrapper 는 `drafts/ingested/youtube/*.md` 에 transcript placeholder 와 cover URL 을 저장한다.
- 실제 전체 자막은 upstream baoyu runtime 을 붙일 때 교체한다.

### 3. 편집 메모
- placeholder 상태면 기사 본문 인용에 직접 사용하지 않는다.
- 영상 요약·팩트 인용 전에는 원 자막 또는 수동 전사본 검토가 필요하다.

## Verify before success
- [ ] `type: youtube` 엔트리가 유효한 URL 또는 video id 를 가짐
- [ ] dry-run 시 video id 파싱이 성공함
- [ ] 생성 markdown 에 transcript 섹션과 cover URL 이 포함됨
- [ ] placeholder 상태임을 편집자에게 명확히 전달함
