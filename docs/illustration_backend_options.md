# Illustration Backend Options

Updated: 2026-04-24

## Provider Status

| Provider | Status | Notes |
|---|---|---|
| Placeholder | merged | Local terminal fallback |
| Pollinations | merged | Free hosted default in TASK_047 |
| HuggingFace | merged | Free token path with allowlisted models |
| OpenAI `gpt-image-1` | skeleton only | Optional paid provider |

## Current Runtime Policy

- Default route: `pollinations`
- Free-only mode: `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=0.0`
- Paid providers are excluded when the monthly cap is zero
- Placeholder remains the final fallback for every chain

## Fallback Chains

- `pollinations -> placeholder`
- `huggingface -> pollinations -> placeholder`
- `openai -> placeholder`
- `placeholder`

## Error Handling

- `IllustrationRateLimitError`: move to next provider
- `IllustrationTimeoutError`: move to next provider
- `IllustrationAuthError`: stop remote attempts and fall back to placeholder
- Other provider errors: continue down the chain when possible
