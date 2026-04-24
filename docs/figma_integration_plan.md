# Figma Integration Plan

Updated: 2026-04-24

This plan covers TASK_042 only. It is a design document for connecting TASK_041 slide JSON to Figma later. It does not implement a live Figma integration.

## 1. MCP Option Comparison Matrix

| Option | License / Terms | Maintenance | Read / Write / Style Coverage | Authentication | Strengths | Weaknesses |
|---|---|---|---|---|---|---|
| Figma official remote MCP | Figma Developer Terms, beta | High, official | Read context, assets, Code Connect, write-to-canvas beta | Hosted MCP auth with Figma account | Lowest integration risk, direct path to frame creation | Beta surface, plan and seat limits apply |
| Figma official local MCP | Figma Developer Terms, beta | High, official | Read context, local assets, desktop-mediated access | Local desktop app session | Useful for designers working locally | Poor fit for CI or unattended jobs |
| Framelink MCP | MIT for server, plus Figma API token usage | High community activity | Read-focused, descriptive JSON for codegen | Personal access token | Smaller payloads, good layout fidelity, easy Cursor setup | Native frame write-back is not the primary focus |
| Talk to Figma MCP | MIT | Medium-high community activity | Read and modify via plugin bridge | Bun server + Figma plugin + local socket | Supports programmatic changes from an agent | More operational complexity, plugin dependency |
| Direct Figma REST wrapper | Figma API terms | We own it | Whatever we build against files/nodes/images APIs | OAuth app or PAT | Maximum control, deterministic mapping from slide schema | Highest build cost and no MCP convenience |

Reference details and URLs are collected in `docs/figma_mcp_comparison.md`.

## 2. Recommendation And Rationale

Recommended path: start with the official hosted Figma MCP, while keeping a direct REST wrapper fallback as the safety valve for TASK_044.

Reasoning:
- TASK_041 already emits a structured card-news JSON payload. The official MCP is the only option in this set with an explicit product direction toward native write-to-canvas from MCP clients, which matches the eventual goal of turning slide JSON into real Figma frames instead of just code.
- It also reuses Figma-native assets, variables, and Code Connect conventions. That reduces the amount of schema translation we would otherwise own in a custom wrapper.
- Framelink is strong for code generation, but this repository needs frame construction, token mapping, and publication-safe layout repeatability more than HTML generation.
- A direct REST wrapper is still worth drafting because it avoids beta coupling. If official MCP write flows remain unstable in TASK_044, we can fall back to deterministic node creation via REST without changing the upstream slide schema.

Rejected as primary choices:
- Official local MCP is useful for manual design workflows, but not for a predictable batch pipeline.
- Talk to Figma MCP is flexible, but it introduces a plugin, a local socket server, and Bun into a repo that currently centers on Python and simple CLIs.

## 3. Slide JSON To Figma Node Mapping

TASK_041 output shape:

```json
{
  "channel": "sns",
  "format": "card-news",
  "slides": [
    {
      "idx": 1,
      "role": "hook",
      "layout": "layout_6",
      "tag": "...",
      "main_copy": "...",
      "sub_copy": "...",
      "highlight": "...",
      "footer": "..."
    }
  ]
}
```

Recommended mapping:

| Slide JSON Field | Figma Node | Node Type | Notes |
|---|---|---|---|
| `slides[n]` | `Slide/{idx}` | FRAME | Base frame size `1080x1350`, auto layout off by default |
| `role` | `meta-role` | STRING metadata or plugin data | Used for lint and template selection |
| `layout` | `meta-layout` | STRING metadata or component variant key | Chooses one of 7 layout templates |
| `tag` | `Tag/Text` + `Tag/Bg` | TEXT + RECTANGLE | Short upper label with colored pill |
| `main_copy` | `MainCopy` | TEXT | Largest type block on slide |
| `sub_copy` | `SubCopy` | TEXT | Secondary explanatory copy |
| `highlight` | `Highlight` | TEXT | Accent pull-quote or stat |
| `footer` | `Footer/Text` + `Footer/Icon` | TEXT + VECTOR/COMPONENT | Branded footer row |
| `idx` | `SlideNumber` | TEXT | Optional visible numbering badge |

Frame defaults:
- Canvas: portrait `1080x1350`
- Background: layout token from `SNS_TOKENS`
- Text styles: map to magazine SNS typography, not ad hoc font sizes
- Asset policy: use Figma-local icons and shapes first, no external icon package assumption

## 4. Layout Component Plans

Shared component slots:
- `tag`: top-left pill
- `main_copy`: headline block
- `sub_copy`: body block
- `highlight`: accent stat or quoted strip
- `footer`: bottom attribution row

Three concrete templates to implement first in TASK_044:

### `layout_1`

- `tag`: top-left, x=72 y=72, pill width hug
- `main_copy`: upper half, x=72 y=180, width=936
- `sub_copy`: below main copy, x=72 y=520, width=780
- `highlight`: right rail card, x=792 y=520, width=216
- `footer`: bottom row, x=72 y=1238, width=936

### `layout_4`

- `tag`: top-center pill, x=auto y=88
- `main_copy`: centered hero block, x=120 y=280, width=840
- `sub_copy`: centered support copy, x=160 y=700, width=760
- `highlight`: CTA band, x=120 y=980, width=840
- `footer`: bottom row, x=72 y=1238, width=936

### `layout_6`

- `tag`: upper-left, x=72 y=72
- `highlight`: top-right numeric or one-line hook, x=760 y=92, width=248
- `main_copy`: middle block, x=72 y=260, width=936
- `sub_copy`: lower explanation, x=72 y=720, width=860
- `footer`: bottom row, x=72 y=1238, width=936

Guideline for remaining templates:
- `layout_2`, `layout_3`, `layout_5`, `layout_7` should stay variant-compatible so slide creation only swaps variant keys and text payload.
- Avoid freeform node math in every slide. Use reusable master components per layout.

## 5. Authentication, Permissions, And Failure Handling

Recommended secret names:
- `FIGMA_ACCESS_TOKEN` for personal testing
- `FIGMA_OAUTH_CLIENT_ID`
- `FIGMA_OAUTH_CLIENT_SECRET`
- `FIGMA_FILE_KEY`
- `FIGMA_TEAM_ID` only if team-scoped automation is later required

Auth model:
- For TASK_044 prototype, a personal access token is acceptable if scope is limited to file access and the target file is explicitly controlled.
- For production or shared automation, move to an OAuth app. Figma documents that OAuth apps are the recommended route and that scopes such as `file_content:read` should be explicitly granted.

Permission design:
- Minimum read scope for schema-to-frame mapping: file content read
- Add write capability only in the implementation phase when frame creation is actually wired
- Keep one dedicated Figma file for generated card-news output instead of mixing into editorial source files

Failure handling:
- If MCP auth fails, stop before mutating anything and emit a structured error
- If write permission is missing, degrade to read-only inspection mode and save a local export plan instead of partial writes
- If the token is valid but rate-limited, enqueue retry with backoff and preserve the unresolved slide bundle under `drafts/`

## 6. Pipeline Integration Guidance

Current handoff point:
- `pipeline/channel_rewriter.py` already emits card-news JSON with `slides`, `meta.total_slides`, and lint metadata.

Recommended future handoff:
1. `channel_rewriter.py --json` writes canonical slide bundle.
2. New TASK_044 script reads that bundle and resolves `layout` to a Figma component template.
3. Figma integration creates or updates one frame per slide.
4. The result URL and node IDs are appended to `logs/card_news.jsonl`.

Suggested log extension for `logs/card_news.jsonl`:

```json
{
  "figma_file_url": "https://www.figma.com/design/...",
  "figma_file_key": "abc123",
  "figma_node_ids": ["1:2", "1:3"],
  "figma_provider": "official-mcp-remote",
  "figma_sync_status": "planned"
}
```

Queueing model:
- Keep Figma sync asynchronous and separate from `channel_rewriter.py` text generation.
- A failed Figma sync should not block article publishing; it should block only the downstream card-news design export path.

## 7. Proposed Scope For TASK_044

Draft scope:
- Add a dedicated `pipeline/figma_card_news_sync.py` CLI.
- Accept `--slides-json`, `--file-key`, `--dry-run`.
- Support official hosted MCP first, direct REST fallback second.
- Implement only the first 3 layout templates in v1: `layout_1`, `layout_4`, `layout_6`.
- Extend logs with file URL, node IDs, sync mode, and failure reason.

Non-goals for TASK_044:
- No plugin marketplace packaging
- No bidirectional sync from Figma back into slide JSON
- No design-token authoring UI inside this repository

## 8. Risks And Open Questions

Risks:
- Official MCP write-to-canvas is beta, so contract changes are possible.
- Figma plan and seat rate limits can make unattended automation brittle for low-tier accounts.
- If layout components are not standardized first, slide JSON can map to visually inconsistent frames.

Open questions:
- Should generated slides live in one shared monthly file or one file per article?
- Do we want generated frames to be editable primitives, or component instances locked to a magazine library?
- Does editorial want deterministic layout selection from `layout_n`, or optional Figma-side overrides after generation?

## Sources

- Official Figma MCP guide: https://github.com/figma/mcp-server-guide
- Figma MCP registry: https://github.com/mcp/com.figma.mcp/mcp
- Figma REST auth: https://developers.figma.com/docs/rest-api/authentication/
- Figma REST endpoints: https://developers.figma.com/docs/rest-api/file-endpoints/
- Figma REST rate limits: https://developers.figma.com/docs/rest-api/rate-limits/
- Framelink site: https://www.framelink.ai/
- Framelink GitHub: https://github.com/glips/figma-context-mcp
- Talk to Figma MCP GitHub: https://github.com/grab/cursor-talk-to-figma-mcp
