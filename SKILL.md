---
name: harmonyos-codelinter
description: Use when working on HarmonyOS ArkTS applications and needing CodeLinter-based detection, triage, or auto-fix of lint violations in .ets/.ts files, especially when requests mention codelinter, lint errors, rule categories, IDE inspections, or safe batch fixes.
---

# HarmonyOS CodeLinter

## Overview

Detect and fix HarmonyOS CodeLinter violations with repeatable steps.
Prioritize official lint output first, then apply safe auto-fixes, and finally verify with a clean re-run.
Default to dynamic, hit-driven context: load only rule details that appear in current lint output.
Use local rule-detail cache first; only fetch remote details when local cache misses.

## Workflow

1. Locate project and lint command
- Prefer official command-line codelinter usage first: `codelinter [options] [dir]`.
- If `codelinter` command is not on PATH but DevEco Studio plugin run directory is available, use:
  `node ./index.js [options] [dir]`.
- If the user gives a command, run it exactly.
- If no command is known, run `scripts/run_harmony_codelinter.sh --project <path>` for command discovery.

2. Run detection and capture logs
- Run lint without fixes to get baseline findings.
- Save output logs for reproducible triage.
- Use `scripts/classify_codelinter_findings.py` to group findings by category.

3. Classify by rule category
- Use [references/rule-categories.md](references/rule-categories.md) as category baseline.
- Use detected rule IDs (for example `@security/no-cycle`) to map findings.
- Keep unknown rule IDs in an `unknown` bucket and report them explicitly.
- Do not load full rule catalog into context unless required.
- For rule examples (positive/negative), read local cache first and fetch remote only for cache misses.

4. Apply fixes in safe order
- First run framework or lint-provided auto-fix.
- Then apply deterministic edits for high-confidence issues only.
- Do not silently change behavior-sensitive code. Ask for confirmation when semantic risk exists.

5. Verify and summarize
- Re-run lint after fixes.
- Report: total findings, fixed findings, remaining findings, unknown categories, and touched files.
- Include exact commands used so results are reproducible.

## Quick Start

```bash
# 1) detect and classify
./scripts/run_harmony_codelinter.sh --project /path/to/app

# 2) detect + fix + re-check (with explicit commands if auto-discovery is not enough)
./scripts/run_harmony_codelinter.sh \
  --project /path/to/app \
  --lint-cmd "codelinter /path/to/app -f json -o /path/to/app/.codelinter-skill/lint-result.json" \
  --fix-cmd "codelinter /path/to/app --fix" \
  --fix

# 3) detect + classify + only load hit-rule examples (positive/negative)
./scripts/run_harmony_codelinter.sh \
  --project /path/to/app \
  --lint-cmd "codelinter" \
  --config-file /path/to/app/code-linter.json5 \
  --with-rule-details
```

## Rules Reference

- Category reference: [references/rule-categories.md](references/rule-categories.md)
- Mapping config used by scripts: [references/rule-categories.json](references/rule-categories.json)
- Full rule catalog by category: [references/rules-catalog.md](references/rules-catalog.md)
- Machine-readable full catalog: [references/rules-catalog.json](references/rules-catalog.json)
- Official CLI guide and options: [references/command-line-codelinter.md](references/command-line-codelinter.md)
- Keep category definitions aligned with the official Huawei guide:
  [HarmonyOS CodeLinter Rules](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-codelinter-rule)

## Scripts

- `scripts/run_harmony_codelinter.sh`
  - Auto-discover lint command, execute lint/fix, save logs, generate categorized summary.
  - Prefer exact category mapping from `rules-catalog.json` before namespace fallback.
  - CLI-first and document-aligned: supports `codelinter [options] [dir]` and plugin `node ./index.js [options] [dir]`.
  - Supports `--config-file` to pass `code-linter.json5`.
  - Optional `--with-rule-details` only fetches details for hit rule IDs in current lint output.
  - Local-first strategy: use `references/rule-details.local.json` first, then fetch missing rules remotely and backfill cache.
- `scripts/classify_codelinter_findings.py`
  - Parse lint logs and group findings by category using exact rule catalog + regex fallback.
- `scripts/fetch_harmony_rules_playwright.py`
  - Use Playwright to fetch dynamic Huawei docs and refresh the full 8-category rule catalog.
- `scripts/fetch_harmony_rule_details_api.py`
  - Fetch per-rule details (description, config, positive and negative examples) via API.
  - Supports hit-driven loading: `--rule-id` or `--rule-ids-file`.
  - Supports local-first cache strategy: `--local-cache`.

## Refresh Rule Metadata

When Huawei updates rules, refresh catalog data with Playwright:

```bash
python3 scripts/fetch_harmony_rules_playwright.py \
  --output-json references/rules-catalog.json \
  --output-md references/rules-catalog.md

# optional: fetch details for selected hit rules only
python3 scripts/fetch_harmony_rule_details_api.py \
  --catalog references/rules-catalog.json \
  --local-cache references/rule-details.local.json \
  --rule-id @security/no-commented-code \
  --rule-id @performance/start-window-icon-check \
  --output-json references/hit-rule-details.json \
  --output-md references/hit-rule-details.md
```

## Guardrails

- Prefer minimal patches over broad rewrites.
- Do not disable rules to make reports pass unless the user explicitly asks.
- When fix confidence is low, stop after detection and propose targeted edits.
