#!/usr/bin/env bash
set -euo pipefail

ADR_DIR="docs/decisions"
echo "📄 Validating ADRs in $ADR_DIR ..."

if [ ! -d "$ADR_DIR" ]; then
  echo "ℹ️  No ADR directory found at $ADR_DIR. Skipping."
  exit 0
fi

# Gather ADR files (exclude template)
mapfile -t ADR_FILES < <(find "$ADR_DIR" -maxdepth 1 -type f -name '*.md' ! -name 'template.md' | sort)
if [ ${#ADR_FILES[@]} -eq 0 ]; then
  echo "ℹ️  No ADR markdown files found. Skipping."
  exit 0
fi

fail=0
warn=0

# Numbering validation
nums=()
for f in "${ADR_FILES[@]}"; do
  base="$(basename "$f")"
  if [[ "$base" =~ ^([0-9]{4})-.*\.md$ ]]; then
    nums+=("${BASH_REMATCH[1]}")
  else
    echo "❌ Invalid ADR filename (expected NNNN-title.md): $base"
    fail=$((fail+1))
  fi
done

# Check duplicates and gaps
if [ ${#nums[@]} -gt 0 ]; then
  dups=$(printf "%s\n" "${nums[@]}" | sort | uniq -d || true)
  if [ -n "$dups" ]; then
    echo "❌ Duplicate ADR numbers detected:"$'\n'"$dups"
    fail=$((fail+1))
  fi

  # Gaps (warning only)
  sorted=$(printf "%s\n" "${nums[@]}" | sort)
  prev=""
  while IFS= read -r n; do
    if [ -n "$prev" ]; then
      expected=$(printf "%04d" $((10#$prev + 1)))
      if [ "$n" != "$expected" ]; then
        echo "⚠️  ADR numbering gap: expected $expected but found $n"
        warn=$((warn+1))
      fi
    fi
    prev="$n"
  done <<< "$sorted"
fi

# Per-file content validation
for f in "${ADR_FILES[@]}"; do
  base="$(basename "$f")"
  # Remove code fence markers to avoid false negatives
  content=$(sed '/^`\{3,\}/d' "$f")

  # Required headings
  if ! grep -qE '^#\s+.+$' <<< "$content"; then
    echo "❌ $base: missing top-level title (e.g., '# Short Title')"
    fail=$((fail+1))
  fi
  if ! grep -q '^## Context and Problem Statement' <<< "$content"; then
    echo "❌ $base: missing '## Context and Problem Statement' section"
    fail=$((fail+1))
  fi
  if ! grep -q '^## Decision Outcome' <<< "$content"; then
    echo "❌ $base: missing '## Decision Outcome' section"
    fail=$((fail+1))
  fi

  # Optional frontmatter validation (only if present)
  first_nonempty=$(sed '/^`\{3,\}/d; /^\s*$/d; q' "$f")
  if [ "$first_nonempty" = "---" ]; then
    fm=$(awk 'BEGIN{inside=0} /^(---)$/ { if (inside==0) { inside=1; next } else { exit } } { if (inside==1) print }' "$f")
    if ! grep -qE '^status:\s*.*' <<< "$fm"; then
      echo "❌ $base: frontmatter present but missing 'status'"
      fail=$((fail+1))
    fi
    if ! grep -qE '^date:\s*[0-9]{4}-[0-9]{2}-[0-9]{2}\s*$' <<< "$fm"; then
      echo "❌ $base: frontmatter present but missing/invalid 'date' (YYYY-MM-DD)"
      fail=$((fail+1))
    fi
    if ! grep -qE '^decision-makers:\s*' <<< "$fm"; then
      echo "❌ $base: frontmatter present but missing 'decision-makers'"
      fail=$((fail+1))
    fi
  else
    echo "ℹ️  $base: no frontmatter block detected (ok; template allows optional metadata)"
  fi
done

echo "— ADR validation summary —"
echo "Warnings: $warn  Errors: $fail"
if [ "$fail" -gt 0 ]; then
  echo "❌ ADR validation failed"
  exit 1
fi
echo "✅ ADR validation passed"
