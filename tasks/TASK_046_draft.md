# TASK_046 Draft (Figma 실구현 후속)

## Meta
- status: draft
- prerequisites: TASK_042
- type: implementation
- note: 기존 "TASK_044 Draft"이 TASK_044(Prompt Caching)와 ID 충돌하여 TASK_046으로 재부여

## Goal
Extend `pipeline/figma_card_news_sync.py` (TASK_042에서 plan builder 형태로 선행 구축됨) with live Figma sync.
TASK_041 card-news slide JSON → Figma frames 실제 생성.

## Proposed Scope
- Support official hosted Figma MCP first
- Accept `--slides-json`, `--file-key`, `--dry-run`
- Implement layouts `layout_1`, `layout_4`, `layout_6`
- Append Figma file URL and node IDs to `logs/card_news.jsonl`

## Non Goals
- No bidirectional sync
- No plugin packaging
- No design token authoring UI
