#!/usr/bin/env python3
import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DOC_API = (
    "https://svc-drcn.developer.huawei.com/community/servlet/consumer/cn/"
    "documentPortal/getDocumentById"
)

HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
RULE_ID_RE = re.compile(r"@[\w-]+/[\w-]+")


def strip_html(s: str) -> str:
    text = TAG_RE.sub(" ", s)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def unescape_code(s: str) -> str:
    return html.unescape(s).strip()


def canonical_rule_id(text: str) -> str:
    text = (text or "").strip()
    match = RULE_ID_RE.search(text)
    return match.group(0) if match else text


def extract_sections(html_content: str):
    matches = list(HEADING_RE.finditer(html_content))
    sections = []

    for idx, match in enumerate(matches):
        heading = strip_html(match.group(2))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(html_content)
        chunk = html_content[start:end]
        text = strip_html(chunk)
        codes = [unescape_code(c) for c in PRE_RE.findall(chunk) if unescape_code(c)]
        sections.append({"heading": heading, "text": text, "codes": codes})

    return sections


def split_intro(html_content: str):
    matches = list(HEADING_RE.finditer(html_content))
    if not matches:
        return strip_html(html_content)
    intro_chunk = html_content[: matches[0].start()]
    return strip_html(intro_chunk)


def fetch_rule(slug: str):
    payload = {"objectId": slug, "language": "cn"}
    req = urllib.request.Request(
        DOC_API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if str(data.get("code")) != "0":
        raise RuntimeError(f"API error: code={data.get('code')} message={data.get('message')}")
    return data["value"]


def url_to_slug(url: str):
    path = urllib.parse.urlparse(url).path
    return path.rstrip("/").split("/")[-1]


def rule_to_detail(anchor: dict):
    expected_rule_id = canonical_rule_id(anchor.get("text", ""))
    url = anchor.get("href", "").strip()
    slug = url_to_slug(url)
    value = fetch_rule(slug)
    html_content = value.get("content", {}).get("content", "")

    sections = extract_sections(html_content)
    positive = []
    negative = []
    config = []
    rule_sets = []
    for s in sections:
        heading = s["heading"]
        if "正例" in heading:
            positive.extend(s["codes"])
        if "反例" in heading:
            negative.extend(s["codes"])
        if ("规则配置" in heading) or ("选项" in heading) or ("配置" in heading):
            config.extend(s["codes"])
        if "规则集" in heading and s["text"]:
            rule_sets.append(s["text"])

    dedupe = lambda xs: list(dict.fromkeys(x for x in xs if x))  # noqa: E731
    positive = dedupe(positive)
    negative = dedupe(negative)
    config = dedupe(config)
    rule_sets = dedupe(rule_sets)

    rid_match = RULE_ID_RE.search(value.get("title", ""))
    actual_rule_id = rid_match.group(0) if rid_match else expected_rule_id

    return {
        "rule_id": actual_rule_id,
        "expected_rule_id": expected_rule_id,
        "slug": slug,
        "url": url,
        "title": value.get("title", ""),
        "description": split_intro(html_content),
        "positive_examples": positive,
        "negative_examples": negative,
        "config_examples": config,
        "rule_sets": rule_sets,
        "section_count": len(sections),
        "sections": sections,
    }


def write_summary(path: Path, payload: dict):
    lines = []
    lines.append("# HarmonyOS CodeLinter Rule Details Summary")
    lines.append("")
    lines.append(f"- Generated at (UTC): {payload['generated_at_utc']}")
    lines.append("- Source: Huawei documentPortal/getDocumentById API")
    lines.append("")

    total = 0
    total_pos = 0
    total_neg = 0
    total_errors = 0
    for c in payload["categories"]:
        total += len(c["rules"])
        total_pos += sum(1 for r in c["rules"] if r["positive_examples"])
        total_neg += sum(1 for r in c["rules"] if r["negative_examples"])
        total_errors += len(c["errors"])

    lines.append(f"- Total rules: {total}")
    lines.append(f"- Rules with positive examples: {total_pos}")
    lines.append(f"- Rules with negative examples: {total_neg}")
    lines.append(f"- Errors: {total_errors}")
    lines.append("")
    lines.append("## Categories")
    lines.append("")

    for c in payload["categories"]:
        lines.append(f"### {c['name']} ({c['namespace']})")
        lines.append(f"- Rules: {len(c['rules'])}")
        lines.append(f"- Errors: {len(c['errors'])}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def load_rule_ids(args) -> set[str]:
    selected_rule_ids = set(canonical_rule_id(rid) for rid in (args.rule_id or []) if rid)
    if args.rule_ids_file:
        for line in Path(args.rule_ids_file).read_text(encoding="utf-8").splitlines():
            rid = canonical_rule_id(line.strip())
            if rid:
                selected_rule_ids.add(rid)
    return selected_rule_ids


def build_cache_map(cache_payload: dict[str, Any]):
    cache_map: dict[str, dict[str, Any]] = {}
    for cat in cache_payload.get("categories", []):
        for rule in cat.get("rules", []):
            rid = rule.get("rule_id")
            if rid:
                cache_map[rid] = rule
    return cache_map


def merge_into_local_cache(local_payload: dict[str, Any], fetched_categories: list[dict[str, Any]]):
    by_name: dict[str, dict[str, Any]] = {}
    for cat in local_payload.get("categories", []):
        by_name[cat.get("name")] = cat

    for cat in fetched_categories:
        name = cat["name"]
        namespace = cat["namespace"]
        target = by_name.get(name)
        if not target:
            target = {"name": name, "namespace": namespace, "rules": [], "errors": []}
            by_name[name] = target
        existing = {r.get("rule_id"): r for r in target.get("rules", [])}
        for rule in cat.get("rules", []):
            rid = rule.get("rule_id")
            if rid:
                existing[rid] = rule
        target["rules"] = sorted(existing.values(), key=lambda r: r.get("rule_id", ""))
        target["namespace"] = namespace
        target.setdefault("errors", [])

    local_payload["generated_at_utc"] = datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()
    local_payload["categories"] = sorted(by_name.values(), key=lambda c: c.get("name", ""))
    return local_payload


def main():
    parser = argparse.ArgumentParser(
        description="Fetch all HarmonyOS CodeLinter rule details (positive/negative examples) via API."
    )
    parser.add_argument("--catalog", required=True, help="Path to rules-catalog.json")
    parser.add_argument("--output-json", required=True, help="Output JSON details path")
    parser.add_argument("--output-md", required=True, help="Output markdown summary path")
    parser.add_argument(
        "--rule-id",
        action="append",
        default=[],
        help="Only fetch details for specific rule ID (repeatable)",
    )
    parser.add_argument(
        "--rule-ids-file",
        help="Optional file with one rule ID per line; only these rules are fetched",
    )
    parser.add_argument(
        "--local-cache",
        help="Optional local cache JSON. Use cache first and fetch remote only for missing rule IDs.",
    )
    parser.add_argument(
        "--max-rules-per-category",
        type=int,
        default=0,
        help="Limit for testing only; 0 means all rules",
    )
    args = parser.parse_args()

    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    selected_rule_ids = load_rule_ids(args)
    local_cache_payload = None
    cache_map: dict[str, dict[str, Any]] = {}
    if args.local_cache:
        cache_path = Path(args.local_cache)
        if cache_path.exists():
            local_cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            cache_map = build_cache_map(local_cache_payload)
        else:
            local_cache_payload = {"generated_at_utc": "", "categories": []}

    categories_out = []
    fetched_for_cache = []
    remote_fetch_count = 0
    cache_hit_count = 0

    for category in catalog.get("categories", []):
        name = category["name"]
        namespace = category["namespace"]
        anchors = category.get("rule_anchors", [])
        if selected_rule_ids:
            anchors = [a for a in anchors if canonical_rule_id(a.get("text", "")) in selected_rule_ids]
        if args.max_rules_per_category > 0:
            anchors = anchors[: args.max_rules_per_category]

        rules = []
        errors = []
        fetched_rules = []
        total = len(anchors)
        for idx, anchor in enumerate(anchors, start=1):
            rid = canonical_rule_id(anchor.get("text", ""))
            print(f"[{name}] {idx}/{total} {rid}", flush=True)
            try:
                if rid in cache_map:
                    detail = dict(cache_map[rid])
                    detail["resolved_from"] = "local-cache"
                    rules.append(detail)
                    cache_hit_count += 1
                else:
                    detail = rule_to_detail(anchor)
                    detail["resolved_from"] = "remote-api"
                    rules.append(detail)
                    fetched_rules.append(detail)
                    remote_fetch_count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "rule_id": rid,
                        "anchor_text": anchor.get("text", ""),
                        "url": anchor.get("href", ""),
                        "error": str(exc),
                    }
                )

        categories_out.append(
            {
                "name": name,
                "namespace": namespace,
                "rules": rules,
                "errors": errors,
            }
        )
        fetched_for_cache.append(
            {"name": name, "namespace": namespace, "rules": fetched_rules, "errors": []}
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_catalog": args.catalog,
        "categories": categories_out,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary(output_md, payload)

    if args.local_cache and local_cache_payload is not None:
        merged = merge_into_local_cache(local_cache_payload, fetched_for_cache)
        cache_path = Path(args.local_cache)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")
    if args.local_cache:
        print(f"Local cache: {args.local_cache}")
    print(f"Cache hits: {cache_hit_count}")
    print(f"Remote fetched: {remote_fetch_count}")


if __name__ == "__main__":
    main()
