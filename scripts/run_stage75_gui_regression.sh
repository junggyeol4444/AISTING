#!/bin/bash
set -u
cd "$(dirname "$0")/.."
: > logs/STAGE75_GUI_ALL.log
passed=0; failed=0; total=0
for script in scripts/gui_*.py; do
  total=$((total+1))
  result=$(timeout 18s xvfb-run -a python "$script" 2>&1)
  rc=$?
  if [ "$rc" -eq 0 ]; then
    passed=$((passed+1)); printf 'PASS %s\n' "$script" >> logs/STAGE75_GUI_ALL.log
  else
    failed=$((failed+1)); printf 'FAIL rc=%s %s\n%s\n' "$rc" "$script" "$result" >> logs/STAGE75_GUI_ALL.log
  fi
done
printf 'SUMMARY total=%s passed=%s failed=%s\n' "$total" "$passed" "$failed" >> logs/STAGE75_GUI_ALL.log
