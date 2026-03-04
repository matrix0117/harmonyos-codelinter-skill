# HarmonyOS CodeLinter Rule Categories

This file is the category baseline used by this skill.

The Huawei guide describes CodeLinter rules in categorized groups and this skill expects 8 buckets.
Because rule namespaces can evolve across HarmonyOS versions, keep this file and
`rule-categories.json` synchronized with the current official documentation:

- https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-codelinter-rule

## Category Set (8 Buckets)

| Category | Namespace Hints | Notes |
| --- | --- | --- |
| typescript-eslint | `@typescript-eslint/` | Common TypeScript/ArkTS base lint rules |
| security | `@security/` | Security hardening checks |
| performance | `@performance/` | Performance and startup/runtime efficiency checks |
| previewer | `@previewer/` | Preview and preview-rendering related checks |
| cross-device-app-dev | `@cross-device-app-dev/` | One-time development and multi-device deployment checks |
| hw-stylistic | `@hw-stylistic/` | ArkTS coding style and maintainability checks |
| correctness | `@correctness/` | Logic correctness and defect prevention checks |
| compatibility | `@compatibility/` | Compatibility checks across API versions/devices |
| custom-or-unknown | `@custom/`, unmatched IDs | Custom, third-party, or unresolved categories |

## Full Rule List

Use these files for complete rule IDs and links per category:

1. `references/rules-catalog.md`
2. `references/rules-catalog.json`

The catalog is generated from dynamically rendered pages through Playwright.

## Update Rule

When the official guide changes category names, update:

1. `references/rule-categories.md`
2. `references/rule-categories.json`
3. Any examples in `SKILL.md`
