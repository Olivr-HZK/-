#!/bin/bash
# 临时脚本：重新生成 voodoo 2026-02-09 ~ 2026-02-15 周报并覆盖数据库
# 用完后可删除： rm regenerate_voodoo_week_20260209_20260215.sh

set -e
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):$PYTHONPATH"
[ -f ".venv/bin/activate" ] && source .venv/bin/activate

echo "重新生成 voodoo 周报：2026-02-09 至 2026-02-15（覆盖数据库）"
python3 workflows/period_workflow.py \
  --start-date 2026-02-09 \
  --end-date 2026-02-15 \
  --companies voodoo \
  --report-save-mode overwrite

echo ""
echo "完成。可删除本脚本: rm regenerate_voodoo_week_20260209_20260215.sh"
