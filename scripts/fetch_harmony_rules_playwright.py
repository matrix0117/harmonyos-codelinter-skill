#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


CATEGORIES = [
    {
        "name": "typescript-eslint",
        "namespace": "@typescript-eslint/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-typescript-eslint",
    },
    {
        "name": "security",
        "namespace": "@security/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-security",
    },
    {
        "name": "performance",
        "namespace": "@performance/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-performance",
    },
    {
        "name": "previewer",
        "namespace": "@previewer/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-previewer",
    },
    {
        "name": "cross-device-app-dev",
        "namespace": "@cross-device-app-dev/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-cross-device-app-dev",
    },
    {
        "name": "hw-stylistic",
        "namespace": "@hw-stylistic/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-hw-stylistic",
    },
    {
        "name": "correctness",
        "namespace": "@correctness/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-codelinter-correctness",
    },
    {
        "name": "compatibility",
        "namespace": "@compatibility/",
        "url": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-codelinter-compatibility",
    },
]


RESULT_RE = re.compile(r"### Result\s*\n(.*?)\n### Ran Playwright code", re.DOTALL)


def run_pw(pwcli: str, args: list[str], env: dict[str, str]) -> str:
    proc = subprocess.run(
        [pwcli, *args], capture_output=True, text=True, env=env, timeout=120
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Playwright command failed: {args}\nexit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc.stdout


def parse_result_block(output: str):
    match = RESULT_RE.search(output)
    if not match:
        raise RuntimeError(f"Could not parse Playwright result block:\n{output}")
    block = match.group(1).strip()
    return json.loads(block)


def build_eval_js(namespace: str) -> str:
    # Extract rule IDs from rendered article text and collect matching anchor entries.
    return f"""() => {{
  const root = document.querySelector('#mark') || document.querySelector('.markdown-body');
  const text = root ? root.innerText : '';
  const ids = Array.from(new Set((text.match(/@[\\w-]+\\/[\\w-]+/g) || [])))
    .filter(id => id.startsWith('{namespace}'))
    .sort();
  const anchors = root
    ? Array.from(root.querySelectorAll('a')).map(a => ({{
        text: (a.textContent || '').trim(),
        href: a.getAttribute('href') || ''
      }}))
    : [];
  const ruleAnchors = anchors.filter(a => a.text.includes('{namespace}'));
  return {{
    ruleIds: ids,
    ruleAnchors: ruleAnchors
  }};
}}"""


def write_markdown(path: Path, payload: dict):
    lines = []
    lines.append("# HarmonyOS CodeLinter Rules Catalog")
    lines.append("")
    lines.append(f"- Generated at (UTC): {payload['generated_at_utc']}")
    lines.append(f"- Source page: {payload['source_page']}")
    lines.append("")
    lines.append("## Categories")
    lines.append("")
    for item in payload["categories"]:
        lines.append(f"### {item['name']} ({item['namespace']})")
        lines.append(f"- Rules: {len(item['rule_ids'])}")
        if item["url"]:
            lines.append(f"- Page: {item['url']}")
        lines.append("")
        for rid in item["rule_ids"]:
            lines.append(f"- `{rid}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch HarmonyOS CodeLinter rule IDs from dynamic pages via Playwright CLI."
    )
    parser.add_argument(
        "--pwcli",
        default=str(Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh"),
        help="Path to playwright_cli.sh wrapper",
    )
    parser.add_argument(
        "--session",
        default="hcrules",
        help="Playwright CLI session name",
    )
    parser.add_argument("--output-json", required=True, help="Output JSON catalog path")
    parser.add_argument("--output-md", required=True, help="Output markdown catalog path")
    args = parser.parse_args()

    env = os.environ.copy()
    env["PLAYWRIGHT_CLI_SESSION"] = args.session

    # Clear stale sessions before batch fetching.
    subprocess.run(
        [args.pwcli, "close-all"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    categories = []
    for cat in CATEGORIES:
        print(f"Fetching {cat['name']} from {cat['url']}", flush=True)
        run_pw(args.pwcli, ["open", cat["url"]], env)
        eval_out = run_pw(args.pwcli, ["eval", build_eval_js(cat["namespace"])], env)
        result = parse_result_block(eval_out)
        categories.append(
            {
                "name": cat["name"],
                "namespace": cat["namespace"],
                "url": cat["url"],
                "rule_ids": sorted(result.get("ruleIds", [])),
                "rule_anchors": result.get("ruleAnchors", []),
            }
        )

    payload = {
        "source_page": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-codelinter-rule",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "categories": categories,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output_md, payload)
    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")


if __name__ == "__main__":
    main()
