---
name: Codex 태스크 구현
about: TASK_*.md 파일을 Codex에 위임할 때 사용
title: "[TASK] TASK_XXX — "
labels: codex-task
assignees: ''
---

## 태스크 ID
`TASK_XXX`

## 태스크 파일
`tasks/TASK_XXX.md`

## 현재 상태
`todo` → `implemented` 목표

## Prerequisites (선행 태스크)
- [ ] TASK_XXX 완료

## 위임 메모
<!-- Codex에 넘길 때 추가 컨텍스트 -->

## 완료 조건 (tasks/TASK_XXX.md에서 복사)
- [ ] ...
- [ ] ...

## 완료 후
```bash
python codex_workflow.py update TASK_XXX implemented
```
