# Illustration Backend Options

Updated: 2026-04-24

This document covers TASK_043 only. It compares candidate image providers and defines the provider interface and fallback chain for `pipeline/illustration_hook.py`. It does not implement a live remote image backend yet.

## 1. Provider Matrix

| Provider | Price Signal | Free Tier | Long Prompt / Text Rendering | Commercial / License | Operational Shape | Notes |
|---|---|---|---|---|---|---|
| OpenAI `gpt-image-1` | Approx. `$0.01` low, `$0.04` medium, `$0.17` high per square image | No standing free API tier | Strong prompt following and editing support | API terms, outputs owned by customer under Services Agreement | Hosted API | Best balanced hosted option for quality plus simple integration |
| Google Gemini image generation | `$0.039` per image on paid tier for Gemini image output | Free tier exists for API testing, but Imagen models are paid tier only | Good for conversational image workflows; Imagen preferred when quality matters | Google API terms | Hosted API | Attractive if a Google stack is already in use |
| Google Imagen on Vertex AI | Imagen 4 Fast `$0.02`, Imagen 4 `$0.04`, Imagen 4 Ultra `$0.06` per image | No free Imagen tier in the cited pricing path | Explicitly positioned for higher-quality image generation | Google Cloud terms | Hosted API | Strong alternative when text rendering and image quality are priority |
| Replicate with `black-forest-labs/flux-schnell` | Public model page lists `$3.00 / thousand output images` | No durable free tier, pay-as-you-go | Fast, usable, but quality depends on chosen model | Apache-2.0 for the cited model | Hosted API over many models | Very flexible, but pricing and behavior vary by selected model |
| Stability AI hosted API | Credit-based pricing; article lists Core and Ultra services, exact cost depends on endpoint | New accounts receive 25 test credits | Good image stack, but credit accounting is less transparent from one table | Stability API terms | Hosted API | Viable paid fallback, but less attractive for a zero-budget-first path |
| Local FLUX.1 Schnell | Inference cost can be near zero after hardware is available | Yes, self-hosted | Good prompt following, text rendering still below top hosted APIs | Apache-2.0 | Local GPU inference | Best zero-recurring-cost option if hardware exists |
| Local Stable Diffusion 3.5 / SDXL class | API cost zero, hardware cost local | Yes, self-hosted | Prompt quality varies, text rendering is weaker than top hosted APIs | Stability Community License for many current Stability weights | Local GPU inference | Strong privacy and cost story, but license and hardware constraints matter |

## 2. Free-Publish Budget Fit

Repository constraint: the magazine targets low or zero marginal publishing cost.

Budget fit by option:
- Best zero-recurring-cost path: local FLUX.1 Schnell or another self-hosted open model on an existing GPU workstation.
- Best low-complexity hosted path: OpenAI `gpt-image-1`, because the integration is simpler and image quality is predictably strong, but it is not zero-cost.
- Best Google path: Imagen 4 Fast when a paid Google billing path already exists and cost per image needs to stay closer to `$0.02`.

Working assumption for weekly scale:
- If each article uses 2 generated illustrations and the magazine publishes roughly 4 issues per month with 20 articles total, that is about 40 images per month.
- Rough monthly image-generation cost at that volume would be approximately:
  - OpenAI medium quality: about `$1.60`
  - Imagen 4 Fast: about `$0.80`
  - Imagen 4 Standard: about `$1.60`
  - Replicate `flux-schnell`: about `$0.12` if the cited per-1k image rate holds for the chosen official model page

These are direct generation estimates only. They exclude retries, edits, and GPU electricity for local inference.

## 3. Recommended Primary Option

Primary recommendation: keep placeholder as default today, and target local FLUX.1 Schnell as the first real backend in TASK_045.

Why:
- It is the only option in this comparison that aligns cleanly with the repo's free-publish constraint while still permitting commercial use under a permissive open license.
- It keeps article prompts and generated assets fully local, which is operationally simple for editorial review and avoids API-spend creep.
- The repo already treats illustration generation as optional enhancement rather than a hard dependency. That makes a local-first backend practical even if it runs only on one editorial machine.

Tradeoff:
- This path assumes access to suitable local hardware. If that assumption fails, the real first implementation should switch to the secondary recommendation below.

## 4. Recommended Secondary Option

Secondary recommendation: OpenAI `gpt-image-1` as the first hosted backend.

Why:
- The API surface is straightforward and already matches the repo's broader tooling direction.
- OpenAI's business terms state that the customer owns output and that customer content is not used to improve services unless the customer explicitly agrees, which is operationally clean for magazine publishing.
- The per-image cost is low enough that a small editorial workload remains inexpensive even without a free tier.

Why it is not the primary choice:
- It introduces recurring API cost and external dependency, which is slightly misaligned with the project constraint favoring free publication.

## 5. Licensing Notes

License summary by option:
- OpenAI API: proprietary service terms; OpenAI's Services Agreement says the customer owns output.
- Google Gemini / Imagen APIs: proprietary Google API and Cloud terms.
- Replicate: platform terms plus model-level license. For `black-forest-labs/flux-schnell`, the model page states Apache-2.0 and commercial use allowed.
- Local FLUX.1 Schnell: Apache-2.0 on the cited Hugging Face model card.
- Local Stability family weights: Stability Community License is free for individuals and organizations under `$1M` annual revenue, with enterprise licensing required above that threshold.

Practical policy for this repo:
- Default to permissive models for first-party self-hosting where possible.
- If a provider has model-level restrictions or revenue caps, log the model and license string in `logs/illustrations.jsonl` for auditability.

## 6. Provider Interface Spec

Chosen interface for this repository:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class IllustrationResult:
    image_path: Path
    provider: str
    model: str
    request_id: str
    license: str
    cost_estimate: float | None = None
    prompt_path: Path | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class IllustrationProvider(ABC):
    name = "base"
    requires_env: tuple[str, ...] = ()

    @abstractmethod
    def generate(
        self,
        prompt: str,
        size: tuple[int, int],
        article_id: str,
        *,
        title: str,
        output_path: Path,
        prompt_path: Path | None = None,
    ) -> IllustrationResult: ...
```

Environment naming proposal:
- `CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `REPLICATE_API_TOKEN`
- `STABILITY_API_KEY`
- `HUGGINGFACE_TOKEN`
- `LOCAL_FLUX_MODEL_PATH`

Why this contract:
- `output_path` keeps file placement deterministic and preserves the current repo behavior.
- `cost_estimate`, `license`, and `provider` give enough audit data without forcing a billing SDK into the hook.

## 7. Fallback Chain Policy

Fallback order:
1. Requested provider if implemented and properly configured
2. Placeholder provider if the provider is unimplemented
3. Placeholder provider if required secrets are missing
4. Placeholder provider if remote generation fails or times out

Non-negotiable behavior:
- `illustration_hook.py` must always return a usable Markdown draft.
- A provider failure must never abort article drafting.
- The fallback event must be recorded in `logs/illustrations.jsonl`.

## 8. Cost Monitoring Design

Proposed `logs/illustrations.jsonl` fields:

```json
{
  "provider": "openai",
  "model": "gpt-image-1",
  "request_id": "req_123",
  "cost_estimate": 0.04,
  "license": "openai-api-terms",
  "provider_context": {
    "requested_provider": "openai",
    "fallback_reason": null
  }
}
```

Monitoring rules:
- Sum `cost_estimate` monthly by provider.
- Alert if monthly generated-image spend crosses a low editorial threshold such as `$10`.
- If `cost_estimate` is `null`, treat the image as local or unknown-cost and exclude from spend alarms.

## 9. Proposed Scope For TASK_045

Draft scope:
- Implement one real backend only.
- Preferred order:
  1. Local FLUX.1 Schnell backend if editorial hardware is confirmed
  2. Otherwise OpenAI `gpt-image-1`
- Add provider selection by env var.
- Add dry-run mode that logs target provider without generating.
- Extend `illustrations.jsonl` with `provider`, `cost_estimate`, and fallback metadata.

Explicit exclusions:
- No unofficial browser automation wrappers
- No reverse-engineered web-only providers
- No provider whose model terms block normal magazine publishing

## Sources

- OpenAI image generation docs: https://platform.openai.com/docs/guides/images/image-generation
- OpenAI pricing: https://openai.com/api/pricing
- OpenAI services agreement: https://openai.com/policies/services-agreement/
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini image generation guide: https://ai.google.dev/gemini-api/docs/imagen-prompt-guide
- Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Vertex AI generative pricing: https://cloud.google.com/vertex-ai/generative-ai/pricing
- Replicate pricing: https://replicate.com/pricing
- Replicate `flux-schnell` model page: https://replicate.com/black-forest-labs/flux-schnell
- FLUX.1 Schnell Hugging Face card: https://huggingface.co/black-forest-labs/FLUX.1-schnell
- Stability license page: https://stability.ai/license
- Stability API pricing update: https://stability.ai/api-pricing-update-25
