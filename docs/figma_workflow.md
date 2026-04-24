# Figma Workflow

This is the free-plan workflow for TASK_046.

## Setup

1. Create a personal Figma draft file that already contains the target slide frames.
2. Generate a personal access token in Figma settings.
3. Set `FIGMA_FILE_KEY` and `FIGMA_ACCESS_TOKEN` in `.env`.

## Build Plan And Paste Package

```bash
python pipeline/figma_card_news_sync.py --slides-json reports/task041_smoke_1.json --file-key <file_key> --dry-run --paste-package
```

Outputs:
- plan JSON in `output/figma_sync/`
- per-slide Markdown files for manual paste

## Manual Editor Flow

1. Open the prepared Figma draft file.
2. Open each `slide_XX_<role>.md` file from the paste package.
3. Paste `tag`, `main_copy`, `sub_copy`, `highlight`, and `footer` into matching text layers.
4. Apply final typography and spacing in Figma.

## Export PNG Assets

```bash
python pipeline/figma_card_news_sync.py --slides-json reports/task041_smoke_1.json --file-key <file_key> --export-images 1:2,1:3
```

This uses the Figma REST image export endpoint and writes PNGs under `output/figma_sync/`.

## Notes

- The free REST path is read and export only. It does not create or mutate Figma nodes.
- Personal drafts are the recommended target because they avoid paid workspace assumptions.
