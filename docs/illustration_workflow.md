# Illustration Workflow

TASK_047 adds a free-first provider chain for article illustrations.

## Provider Selection

- `pollinations`: default free hosted path
- `huggingface`: free token path, falls back to `pollinations`
- `placeholder`: local placeholder only
- `openai`: optional paid path, disabled by default when monthly cap is `0.0`

## Recommended Default

```env
CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER=pollinations
CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=0.0
```

This keeps the system on free providers only.

## Optional HuggingFace Setup

1. Create a Hugging Face token.
2. Set `HUGGINGFACE_TOKEN`.
3. Optionally override `HUGGINGFACE_IMAGE_MODEL` with an allowlisted model.

## Fallback Behavior

- `IllustrationRateLimitError` and `IllustrationTimeoutError` move to the next provider in the chain.
- `IllustrationAuthError` stops the chain and drops straight to `placeholder`.
- `placeholder` is always the terminal fallback.

## Logging

Each generated illustration appends an entry to `logs/illustrations.jsonl` with:
- `provider`
- `provider_chain`
- `cost_estimate`
- `license`
- `provider_context`

Monthly cost totals are also aggregated in `data/illustration_cost_YYYY-MM.json`.
