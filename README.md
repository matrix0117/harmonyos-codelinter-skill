# HarmonyOS CodeLinter Skill

一个用于 HarmonyOS ArkTS 项目的 CodeLinter 检测与修复技能包，支持：

- 通过命令行优先执行 `codelinter [options] [dir]`
- 按 8 大官方分类归类规则与告警
- 基于命中规则按需加载详情（正例/反例/配置）
- 本地缓存优先，缓存缺失时再拉取远端详情
- 支持安全自动修复并复检

## 目录结构

```text
.
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── run_harmony_codelinter.sh
│   ├── classify_codelinter_findings.py
│   ├── fetch_harmony_rules_playwright.py
│   └── fetch_harmony_rule_details_api.py
└── references/
    ├── command-line-codelinter.md
    ├── rule-categories.json
    ├── rule-categories.md
    ├── rules-catalog.json
    ├── rules-catalog.md
    ├── rule-details.local.json
    └── rule-details.local.md
```

## 快速使用

### 1) 只检测并分类

```bash
./scripts/run_harmony_codelinter.sh --project /path/to/app
```

### 2) 检测 + 自动修复 + 复检

```bash
./scripts/run_harmony_codelinter.sh \
  --project /path/to/app \
  --fix
```

### 3) 检测 + 命中规则详情（正例/反例）按需加载

```bash
./scripts/run_harmony_codelinter.sh \
  --project /path/to/app \
  --config-file /path/to/app/code-linter.json5 \
  --with-rule-details
```

## 关键脚本

- `scripts/run_harmony_codelinter.sh`
  - 自动发现 lint 命令（`codelinter`、插件 `node ./index.js`、常见项目 lint 命令）
  - 生成日志、分类总结、命中规则清单与规则详情
- `scripts/classify_codelinter_findings.py`
  - 将告警按规则分类汇总
- `scripts/fetch_harmony_rules_playwright.py`
  - 用 Playwright 抓取动态文档，刷新 8 类规则目录
- `scripts/fetch_harmony_rule_details_api.py`
  - 获取规则详情（描述、配置、正例、反例）
  - 支持本地缓存优先和按 ruleId 定向拉取

## 产物说明

`run_harmony_codelinter.sh` 默认在项目下输出 `.codelinter-skill/`：

- `lint.log`：完整 lint/fix 日志
- `lint-result.json`：JSON 格式 lint 结果（若命令支持）
- `summary.md`：按分类汇总
- `hit-rule-ids.txt`：命中规则 ID
- `hit-rule-details.json` / `hit-rule-details.md`：命中规则详情（启用 `--with-rule-details`）

## 刷新规则数据

```bash
python3 scripts/fetch_harmony_rules_playwright.py \
  --output-json references/rules-catalog.json \
  --output-md references/rules-catalog.md
```

可选：只拉取指定规则详情并回填本地缓存

```bash
python3 scripts/fetch_harmony_rule_details_api.py \
  --catalog references/rules-catalog.json \
  --local-cache references/rule-details.local.json \
  --rule-id @security/no-commented-code \
  --rule-id @performance/start-window-icon-check \
  --output-json references/hit-rule-details.json \
  --output-md references/hit-rule-details.md
```

## 参考文档

- Huawei CodeLinter 规则总览：
  https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-codelinter-rule
- Huawei CodeLinter 命令行说明：
  https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-code-linter
