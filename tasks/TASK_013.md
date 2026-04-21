# TASK_013 — 주간 브리프 E2E 스모크 테스트

## 메타
- **status**: todo
- **prerequisites**: TASK_012
- **예상 소요**: 45분
- **서브에이전트 분할**: 불필요
- **Phase**: 2 (운영 준비)

---

## 목적
주간 브리프 발행 파이프라인 전체(브리프 → 초안 → 팩트체크 → Ghost 드래프트)를
**실제 API 호출 없이 mock으로 검증**한다.
CI·로컬에서 리그레션 방지용으로 재사용 가능하게 한다.

---

## 구현 명세

### 생성할 파일: `scripts/test_e2e.py`

### CLI
```bash
# 전체 E2E (mock)
python scripts/test_e2e.py

# 실제 API 사용 (비용 주의)
python scripts/test_e2e.py --live

# 특정 단계만
python scripts/test_e2e.py --step brief
python scripts/test_e2e.py --step draft
python scripts/test_e2e.py --step factcheck
python scripts/test_e2e.py --step ghost
```

### 검증 흐름 (mock 모드)

```
1. brief_generator.generate_brief(topic="테스트 토픽")
   → anthropic.Anthropic() 를 patch 해서 고정 JSON 반환
   → 반환값 스키마 검증 (working_title, angle, outline, evidence_map 등)
   → drafts/ 임시 파일 생성 확인

2. draft_writer.write_section(brief, "서론")
   → mock 응답: "# 서론\n\n테스트 본문..."
   → 섹션별 호출 반복 확인

3. fact_checker.run_factcheck(draft_text, source_bundle)
   → mock 응답: 마크다운 표 + 위험도 요약
   → logs/factcheck_*.json 생성 확인

4. ghost_client.create_post(title, html, status="draft")
   → requests.post 를 patch 해서 가짜 post_id 반환
   → JWT 토큰 생성 경로는 실제로 실행 (키 포맷 검증)
```

### Mock 전략
- `unittest.mock.patch` 로 `anthropic.Anthropic.messages.stream` 교체
- Ghost는 `requests.post` patch
- 실제 파일 I/O는 `tempfile.TemporaryDirectory()` 에 격리
- 테스트 후 임시 파일 자동 정리

### 출력 형식
```
=== E2E 스모크 테스트 (mock 모드) ===

[1/4] brief_generator
  ✅ generate_brief() 호출 성공
  ✅ 반환 JSON 스키마 7개 키 모두 존재
  ✅ drafts/brief_test.json 생성 확인 (127 bytes)

[2/4] draft_writer
  ✅ write_section("서론") 성공
  ✅ write_section("본론") 성공
  ✅ drafts/draft_test.md 생성 확인 (450 bytes)

[3/4] fact_checker
  ✅ run_factcheck() 성공
  ✅ logs/factcheck_*.json 생성 (request_id 포함)
  ✅ 출력에 "전체 위험도" 섹션 포함

[4/4] ghost_client
  ✅ JWT 토큰 생성 성공
  ✅ create_post() mock 응답 파싱 성공
  ✅ 반환값에 post_id, url, status 모두 포함

=== 결과: 12 통과 / 0 실패 — 전체 흐름 정상 ===
```

### --live 모드
- 환경변수 키가 모두 설정된 상태에서만 실행 가능
- `check_env.py --strict` 내부 호출 후 통과 시에만 진행
- 각 단계 실행 시간·토큰 사용량·비용 추산 출력

---

## 완료 조건
- [ ] `scripts/test_e2e.py` 생성
- [ ] mock 모드로 전체 4단계 검증 통과
- [ ] `--step` 필터로 개별 단계 독립 실행 가능
- [ ] `--live` 모드는 check_env.py --strict 선행 호출
- [ ] 출력이 시각적으로 명확 (✅❌)
- [ ] exit code: 전체 통과 0, 하나라도 실패 1
- [ ] 임시 파일 자동 정리 (`drafts/` `logs/` 에 잔재 없음)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_013 implemented
```
