---
name: baoyu-url-to-markdown
description: 외부 단일 URL을 매거진용 markdown 초안으로 수집하는 래퍼 스킬. "웹페이지 저장", "url to markdown", "단일 기사 수집" 요청에 사용.
allowed-tools: Bash, Read, Write
---

<!-- source: jimliu/baoyu-skills@8c17d77209b030a97d1746928ae348c99fefa775 -->

# URL to Markdown (Magazine Wrapper)

## 언제 사용
- RSS가 아니라 단일 기사 URL을 바로 source registry에 넣고 싶을 때
- `config/feeds.yml`에 `type: url` 엔트리를 추가해 수집 파이프라인에 태우고 싶을 때
- 한국어 매거진 초안용으로 본문 요약 markdown이 먼저 필요할 때

## 절차 (Systematic)

### 1. 입력 확인
- URL과 언어, 토픽, 공식 출처 여부를 확인한다.
- 동적 렌더링이 심한 사이트면 wrapper 결과를 provisional 로 취급한다.

### 2. 저장소 래퍼 경로 사용
```bash
python scripts/run_source_ingest.py --feeds-config config/feeds.yml --dry-run
```
- 실제 프로젝트에서는 `pipeline/source_ingester.py` 의 `type: url` 경로가 본문 요약 markdown을 생성한다.
- 산출물은 `drafts/ingested/url/*.md` 에 기록된다.

### 3. 품질 점검
- 제목과 첫 문단이 정상 추출됐는지 확인한다.
- 중요 표·코드블록이 누락되면 upstream baoyu skill 또는 수동 정제를 권장한다.

## Verify before success
- [ ] `type: url` 엔트리가 `config/feeds.yml` 에 정의됨
- [ ] dry-run 또는 실제 수집이 오류 없이 끝남
- [ ] 생성 markdown 에 한글 운영 메모와 source URL 이 포함됨
- [ ] registry 등록 또는 후속 등록 경로가 명확함
