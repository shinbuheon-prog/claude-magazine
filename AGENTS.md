# AGENTS.md — Codex 서브에이전트 가이드

> 이 파일은 Codex 에이전트가 태스크를 위임받았을 때 가장 먼저 읽어야 할 파일입니다.
> 프로젝트 전체 컨텍스트는 CLAUDE.md를 참조하세요.

---

## 에이전트 행동 규칙

1. **CLAUDE.md를 먼저 읽고 시작**
2. **할당된 TASK_*.md의 완료 조건을 전부 통과**해야 구현 완료
3. 구현 완료 시 반드시 실행:
   ```bash
   python codex_workflow.py update TASK_00X implemented
   ```
4. 다른 TASK에 의존하는 함수가 미완성이면 **stub(빈 함수 + TODO 주석)**으로 처리하고 진행
5. 새 파일 생성 시 **CLAUDE.md의 코딩 규칙** 준수:
   - 스트리밍 필수
   - request_id → `logs/` 저장 필수
   - argparse CLI + `--dry-run` 옵션
   - `if __name__ == "__main__":` 스모크 테스트 포함

---

## 병렬 실행 가능한 태스크 조합

```
1단계 (동시 실행 가능)
  TASK_001  ←── 반드시 먼저
  
2단계 (TASK_001 완료 후 동시 실행 가능)
  TASK_002  Ghost CMS
  TASK_003  Claude 파이프라인
  TASK_004  출처 레지스트리
  TASK_008  Langfuse (003과 병렬)

3단계 (002+003 완료 후)
  TASK_005  팩트체크 (003+004 필요)
  TASK_006  주간 브리프 발행 (002+003 필요)

4단계 (003~006 모두 완료 후)
  TASK_007  n8n 자동화
```

---

## 태스크별 핵심 파일

| TASK | 생성/수정할 파일 | 테스트 커맨드 |
|---|---|---|
| TASK_001 | data/ drafts/ logs/ 폴더 | `python codex_workflow.py sync` |
| TASK_002 | `pipeline/ghost_client.py` | `python pipeline/ghost_client.py` |
| TASK_003 | `pipeline/brief_generator.py`, `pipeline/draft_writer.py` | `python pipeline/brief_generator.py --topic "TEST"` |
| TASK_004 | `pipeline/source_registry.py` | `python pipeline/source_registry.py` |
| TASK_005 | `pipeline/fact_checker.py` | `python pipeline/fact_checker.py --draft /tmp/test.md` |
| TASK_006 | `scripts/run_weekly_brief.py` | `python scripts/run_weekly_brief.py --topic "TEST" --dry-run` |
| TASK_007 | `n8n/workflow_*.json` | n8n UI import 확인 |
| TASK_008 | `pipeline/observability.py` + 각 모듈 수정 | Langfuse 대시보드 trace 확인 |

---

## 환경 설정 체크 (구현 시작 전 확인)

```bash
# 패키지 설치 확인
pip install -r requirements.txt

# .env 존재 확인
ls .env  # 없으면 "cp .env.example .env" 실행 안내

# 보드 상태 확인
python codex_workflow.py list
```

---

## 절대 하지 말아야 할 것

- ❌ `.env` 파일을 커밋하거나 키를 코드에 하드코딩
- ❌ `claude-opus-4-7`를 일반 기사 브리프에 사용 (비용 폭증)
- ❌ request_id 로깅 생략
- ❌ 스트리밍 없이 `client.messages.create()` 직접 호출 (긴 요청에서 timeout 위험)
- ❌ `source_registry` 없이 source_id를 임의로 생성
