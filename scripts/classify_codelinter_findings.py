#!/usr/bin/env python3
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


RULE_ID_PATTERN = re.compile(r"@[\w-]+/[\w-]+")


def load_mapping(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    ordered = data.get("ordered_categories", [])
    fallback = data.get("fallback_category", "custom-or-unknown")
    compiled = []
    for item in ordered:
        name = item["name"]
        patterns = [re.compile(p) for p in item.get("patterns", [])]
        compiled.append((name, patterns))
    return compiled, fallback


def load_catalog(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    by_rule_id = {}
    for category in data.get("categories", []):
        name = category.get("name")
        for rid in category.get("rule_ids", []):
            by_rule_id[rid] = name
    return by_rule_id


def category_for(rule_id: str, mapping, fallback: str) -> str:
    for name, patterns in mapping:
        if any(p.search(rule_id) for p in patterns):
            return name
    return fallback


def main():
    parser = argparse.ArgumentParser(
        description="Classify HarmonyOS CodeLinter findings by category."
    )
    parser.add_argument("--input", required=True, help="Path to lint log file")
    parser.add_argument("--mapping", required=True, help="Path to category JSON mapping")
    parser.add_argument(
        "--catalog",
        help="Optional rules catalog JSON for exact rule-id category mapping",
    )
    parser.add_argument("--output", required=True, help="Path to markdown summary output")
    args = parser.parse_args()

    input_path = Path(args.input)
    mapping_path = Path(args.mapping)
    output_path = Path(args.output)

    text = input_path.read_text(encoding="utf-8", errors="ignore")
    rule_ids = RULE_ID_PATTERN.findall(text)

    mapping, fallback = load_mapping(mapping_path)
    catalog_map = load_catalog(Path(args.catalog)) if args.catalog else {}
    buckets = defaultdict(list)
    unknown_in_catalog = set()
    for rid in rule_ids:
        if rid in catalog_map:
            buckets[catalog_map[rid]].append(rid)
        else:
            buckets[category_for(rid, mapping, fallback)].append(rid)
            if args.catalog:
                unknown_in_catalog.add(rid)

    lines = []
    lines.append("# CodeLinter Category Summary")
    lines.append("")
    lines.append(f"- Total findings: {len(rule_ids)}")
    lines.append(f"- Unique rule IDs: {len(set(rule_ids))}")
    if args.catalog:
        lines.append(f"- Rule IDs not found in catalog: {len(unknown_in_catalog)}")
    lines.append("")
    lines.append("## By Category")
    lines.append("")

    ordered_names = [name for name, _ in mapping] + [fallback]
    for name in ordered_names:
        ids = buckets.get(name, [])
        lines.append(f"### {name}")
        lines.append(f"- Findings: {len(ids)}")
        unique_ids = sorted(set(ids))
        if unique_ids:
            lines.append("- Rule IDs:")
            for rid in unique_ids[:30]:
                lines.append(f"  - `{rid}`")
            if len(unique_ids) > 30:
                lines.append(f"  - `... ({len(unique_ids) - 30} more)`")
        lines.append("")

    if args.catalog and unknown_in_catalog:
        lines.append("## Rule IDs Not Found In Catalog")
        lines.append("")
        for rid in sorted(unknown_in_catalog):
            lines.append(f"- `{rid}`")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote summary: {output_path}")


if __name__ == "__main__":
    main()
