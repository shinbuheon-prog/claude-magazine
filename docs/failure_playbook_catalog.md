# Failure Playbook Catalog

Generated from [spec/failure_playbook.yml](../spec/failure_playbook.yml).

## plan_loaded

- `plan_file_missing`: `FileNotFoundError.*drafts/issues`
- `yaml_parse_error`: `yaml.YAMLError|could not determine a constructor|while parsing`

## quality_gate

- `article_status_not_approved`: `status=(draft|lint)`
- `editorial_lint_fail`: `lint_fail|editorial_lint`

## disclosure_injected

- `disclosure_write_failed`: `disclosure.*(write|permission|denied)`
- `disclosure_content_conflict`: `disclosure.*conflict|ai disclosure`

## pdf_compile

- `puppeteer_timeout`: `TimeoutError.*puppeteer|Navigation timeout`
- `vite_build_fail`: `vite.*build failed|npm run build`

## ghost_publish

- `jwt_401`: `401.*Unauthorized|JWT|Admin API Key`
- `publish_confirmation_missing`: `--confirm is required`

## newsletter

- `members_api_disabled`: `Members API.*disabled|newsletter`
- `publish_flag_missing`: `--publish not set`

## sns

- `channel_rewriter_timeout`: `timeout.*channel_rewriter|channel_rewriter.*timeout`
- `publish_flag_missing`: `--publish not set|--skip-sns`
