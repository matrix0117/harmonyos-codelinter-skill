# HarmonyOS CodeLinter CLI (Official)

Source:

- https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-code-linter#section12737634185911
- https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-command-line-codelinter

## Command Format

Recommended command format:

```bash
codelinter [options] [dir]
```

`dir` is optional. If not provided, the current working directory is used.

For DevEco Studio plugin `run` directory usage:

```bash
node ./index.js [options] [dir]
```

## Options

- `--config` / `-c <filepath>`: Use a specific `code-linter.json5` config file.
- `--fix`: Run QuickFix for supported findings.
- `--format` / `-f`: Output format. Supported: `default`, `json`, `xml`, `html`.
- `--output` / `-o <filepath>`: Save result to a file instead of printing full output.
- `--version` / `-v`: Show codelinter version.
- `--product` / `-p <productName>`: Select product for multi-product projects.
- `--incremental` / `-i`: Check incremental files in Git (added/modified/renamed).
- `--help` / `-h`: Show help.
- `--exit-on` / `-e <levels>`: Non-zero exit code policy for `error,warn,suggestion`.

## Practical Commands

```bash
# Basic check in project root
codelinter

# Check specific project path
codelinter /path/to/project

# Check with explicit config file
codelinter -c /path/to/code-linter.json5 /path/to/project

# Check and auto-fix supported findings
codelinter -c /path/to/code-linter.json5 /path/to/project --fix

# CI-friendly JSON output file
codelinter /path/to/project -f json -o /tmp/lint-result.json

# Fail CI on selected severities
codelinter /path/to/project -e error,warn
```
