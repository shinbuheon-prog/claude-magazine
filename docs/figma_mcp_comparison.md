# Figma MCP Comparison

Updated: 2026-04-24

This note compares realistic options for turning TASK_041 card-news slide JSON into Figma frames later.

## Option Matrix

| Option | Type | License / Terms | Maintenance Signal | Read / Write Coverage | Auth Model | Notes |
|---|---|---|---|---|---|---|
| Figma official remote MCP | Hosted MCP | Figma Developer Terms / beta | Official, actively documented | Read + write-to-canvas beta | Figma account auth via hosted MCP | Best long-term fit if write-back to frames is required |
| Figma official local MCP | Desktop-hosted MCP | Figma Developer Terms / beta | Official, tied to desktop app | Read + local asset serving | Local desktop session | Good for designer-driven local iteration, weaker for unattended automation |
| Framelink MCP (`GLips/Figma-Context-MCP`) | Community MCP | MIT + Figma token usage | Very active GitHub project | Read-focused, layout/context optimized | Personal access token | Strong for codegen context, weaker for native frame creation |
| Talk to Figma MCP (`grab/cursor-talk-to-figma-mcp`) | Community MCP + plugin | MIT | Active GitHub project | Read + modify via plugin bridge | Bun server + Figma plugin + local socket | Powerful, but more moving parts than this repo needs |
| Direct Figma REST wrapper | Custom integration | Figma API terms | We own maintenance | Read + write only what we implement | OAuth app or PAT | Highest control, highest implementation cost |

## Source Links

- Official MCP guide: https://github.com/figma/mcp-server-guide
- Official MCP registry page: https://github.com/mcp/com.figma.mcp/mcp
- Figma REST authentication: https://developers.figma.com/docs/rest-api/authentication/
- Figma REST file endpoints: https://developers.figma.com/docs/rest-api/file-endpoints/
- Figma REST rate limits: https://developers.figma.com/docs/rest-api/rate-limits/
- Framelink MCP repo: https://github.com/glips/figma-context-mcp
- Framelink site: https://www.framelink.ai/
- Talk to Figma MCP repo: https://github.com/grab/cursor-talk-to-figma-mcp
