#!/usr/bin/env bash
set -euo pipefail

PROJECT=""
LINT_CMD=""
FIX_CMD=""
RUN_FIX="false"
OUT_DIR=""
WITH_RULE_DETAILS="false"
CONFIG_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --lint-cmd)
      LINT_CMD="$2"
      shift 2
      ;;
    --fix-cmd)
      FIX_CMD="$2"
      shift 2
      ;;
    --fix)
      RUN_FIX="true"
      shift
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --with-rule-details)
      WITH_RULE_DETAILS="true"
      shift
      ;;
    --config-file)
      CONFIG_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  echo "Missing required --project <path>" >&2
  exit 2
fi

if [[ -z "$OUT_DIR" ]]; then
  OUT_DIR="$PROJECT/.codelinter-skill"
fi

mkdir -p "$OUT_DIR"
LOG_FILE="$OUT_DIR/lint.log"
SUMMARY_FILE="$OUT_DIR/summary.md"
LINT_JSON_FILE="$OUT_DIR/lint-result.json"
CLASSIFY_INPUT_FILE="$OUT_DIR/classify-input.txt"
HIT_RULES_FILE="$OUT_DIR/hit-rule-ids.txt"
DETAILS_JSON_FILE="$OUT_DIR/hit-rule-details.json"
DETAILS_MD_FILE="$OUT_DIR/hit-rule-details.md"

detect_lint_cmd() {
  if [[ -n "$LINT_CMD" ]]; then
    echo "$LINT_CMD"
    return 0
  fi

  if command -v codelinter >/dev/null 2>&1; then
    if [[ -n "$CONFIG_FILE" ]]; then
      echo "codelinter -c \"$CONFIG_FILE\" \"$PROJECT\" -f json -o \"$LINT_JSON_FILE\""
    else
      echo "codelinter \"$PROJECT\" -f json -o \"$LINT_JSON_FILE\""
    fi
    return 0
  fi

  if [[ -n "${CODELINTER_RUN_DIR:-}" ]] && [[ -f "${CODELINTER_RUN_DIR}/index.js" ]] && command -v node >/dev/null 2>&1; then
    if [[ -n "$CONFIG_FILE" ]]; then
      echo "node \"${CODELINTER_RUN_DIR}/index.js\" -c \"$CONFIG_FILE\" \"$PROJECT\" -f json -o \"$LINT_JSON_FILE\""
    else
      echo "node \"${CODELINTER_RUN_DIR}/index.js\" \"$PROJECT\" -f json -o \"$LINT_JSON_FILE\""
    fi
    return 0
  fi

  if [[ -x "$PROJECT/hvigorw" ]]; then
    echo "./hvigorw lint"
    return 0
  fi

  if [[ -f "$PROJECT/package.json" ]]; then
    if command -v pnpm >/dev/null 2>&1; then
      echo "pnpm lint"
      return 0
    fi
    if command -v npm >/dev/null 2>&1; then
      echo "npm run lint"
      return 0
    fi
  fi

  echo ""
}

EXEC_LINT_CMD="$(detect_lint_cmd)"
if [[ -z "$EXEC_LINT_CMD" ]]; then
  echo "Could not auto-detect lint command. Pass --lint-cmd explicitly." >&2
  exit 3
fi

echo "Project: $PROJECT"
echo "Lint command: $EXEC_LINT_CMD"
echo "Output dir: $OUT_DIR"

(
  cd "$PROJECT"
  set +e
  bash -lc "$EXEC_LINT_CMD" >"$LOG_FILE" 2>&1
  LINT_EXIT=$?
  set -e
  echo "Lint exit code: $LINT_EXIT"
)

if [[ "$RUN_FIX" == "true" ]]; then
  if [[ -z "$FIX_CMD" ]]; then
    if [[ "$EXEC_LINT_CMD" == *"codelinter"* ]]; then
      if [[ -n "$CONFIG_FILE" ]]; then
        FIX_CMD="codelinter -c \"$CONFIG_FILE\" \"$PROJECT\" --fix"
      else
        FIX_CMD="codelinter \"$PROJECT\" --fix"
      fi
    elif [[ "$EXEC_LINT_CMD" == *"index.js"* ]]; then
      if [[ -n "$CONFIG_FILE" ]]; then
        FIX_CMD="node \"${CODELINTER_RUN_DIR}/index.js\" -c \"$CONFIG_FILE\" \"$PROJECT\" --fix"
      else
        FIX_CMD="node \"${CODELINTER_RUN_DIR}/index.js\" \"$PROJECT\" --fix"
      fi
    elif [[ "$EXEC_LINT_CMD" == "npm run lint" ]]; then
      FIX_CMD="npm run lint -- --fix"
    elif [[ "$EXEC_LINT_CMD" == "pnpm lint" ]]; then
      FIX_CMD="pnpm lint -- --fix"
    fi
  fi

  if [[ -n "$FIX_CMD" ]]; then
    echo "Fix command: $FIX_CMD"
    (
      cd "$PROJECT"
      set +e
      bash -lc "$FIX_CMD" >>"$LOG_FILE" 2>&1
      FIX_EXIT=$?
      set -e
      echo "Fix exit code: $FIX_EXIT"
      echo "--- Re-running lint after fix ---" >>"$LOG_FILE"
      bash -lc "$EXEC_LINT_CMD" >>"$LOG_FILE" 2>&1 || true
    )
  else
    echo "No fix command determined. Skipping --fix." >&2
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAPPING_FILE="$SCRIPT_DIR/../references/rule-categories.json"
CATALOG_FILE="$SCRIPT_DIR/../references/rules-catalog.json"
LOCAL_DETAIL_CACHE_FILE="$SCRIPT_DIR/../references/rule-details.local.json"

cat "$LOG_FILE" >"$CLASSIFY_INPUT_FILE"
if [[ -f "$LINT_JSON_FILE" ]]; then
  printf "\n\n# lint-result.json\n" >>"$CLASSIFY_INPUT_FILE"
  cat "$LINT_JSON_FILE" >>"$CLASSIFY_INPUT_FILE"
fi

python3 "$SCRIPT_DIR/classify_codelinter_findings.py" \
  --input "$CLASSIFY_INPUT_FILE" \
  --mapping "$MAPPING_FILE" \
  --catalog "$CATALOG_FILE" \
  --output "$SUMMARY_FILE"

if [[ "$WITH_RULE_DETAILS" == "true" ]]; then
  rg -o "@[[:alnum:]_-]+/[[:alnum:]_-]+" "$CLASSIFY_INPUT_FILE" | sort -u >"$HIT_RULES_FILE" || true
  if [[ -s "$HIT_RULES_FILE" ]]; then
    python3 "$SCRIPT_DIR/fetch_harmony_rule_details_api.py" \
      --catalog "$CATALOG_FILE" \
      --rule-ids-file "$HIT_RULES_FILE" \
      --local-cache "$LOCAL_DETAIL_CACHE_FILE" \
      --output-json "$DETAILS_JSON_FILE" \
      --output-md "$DETAILS_MD_FILE"
  else
    echo "No rule IDs found in lint output. Skip detail fetch." >&2
  fi
fi

echo "Done."
echo "Log: $LOG_FILE"
if [[ -f "$LINT_JSON_FILE" ]]; then
  echo "Lint JSON: $LINT_JSON_FILE"
fi
echo "Summary: $SUMMARY_FILE"
if [[ "$WITH_RULE_DETAILS" == "true" ]]; then
  echo "Hit rule IDs: $HIT_RULES_FILE"
  echo "Hit rule details JSON: $DETAILS_JSON_FILE"
  echo "Hit rule details Markdown: $DETAILS_MD_FILE"
  echo "Local detail cache: $LOCAL_DETAIL_CACHE_FILE"
fi
