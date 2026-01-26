#!/bin/bash
# Bash脚本：每周定时运行时间段工作流
# 用于 macOS/Linux Cron 任务
# 功能：生成上周的竞品周报

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 设置 Python 路径，确保能找到项目根目录的模块（如 env_loader）
export PYTHONPATH="$(pwd):$PYTHONPATH"

# 激活虚拟环境（如果使用虚拟环境）
# 如果使用虚拟环境，取消下面这行的注释并修改路径
# source .venv/bin/activate

# 日志文件路径
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# 计算上周的日期范围（周一到周日）
# macOS 和 Linux 的日期计算方式不同
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    # 获取今天是星期几（0=周日, 1=周一, ..., 6=周六）
    DAY_OF_WEEK=$(date +%w)
    if [ "$DAY_OF_WEEK" -eq 0 ]; then
        DAY_OF_WEEK=7  # 周日转换为7
    fi
    # 上周的结束日期（上周日）= 今天 - DAY_OF_WEEK 天
    LAST_WEEK_END=$(date -v-${DAY_OF_WEEK}d +%Y-%m-%d)
    # 上周的开始日期（上周一）= 上周日 - 6 天
    LAST_WEEK_START=$(date -v-$(($DAY_OF_WEEK + 6))d +%Y-%m-%d)
else
    # Linux
    DAY_OF_WEEK=$(date +%w)
    if [ "$DAY_OF_WEEK" -eq 0 ]; then
        DAY_OF_WEEK=7  # 周日转换为7
    fi
    # 上周的结束日期（上周日）
    LAST_WEEK_END=$(date -d "$DAY_OF_WEEK days ago" +%Y-%m-%d)
    # 上周的开始日期（上周一）
    LAST_WEEK_START=$(date -d "$(($DAY_OF_WEEK + 6)) days ago" +%Y-%m-%d)
fi

LOG_FILE="$LOG_DIR/weekly_period_workflow_$(date +%Y-%m-%d).log"

# 记录开始时间
START_TIME=$(date)

echo "========================================" | tee -a "$LOG_FILE"
echo "开始执行每周时间段工作流任务" | tee -a "$LOG_FILE"
echo "目标: 生成上周的竞品周报" | tee -a "$LOG_FILE"
echo "时间段: $LAST_WEEK_START 至 $LAST_WEEK_END" | tee -a "$LOG_FILE"
echo "时间: $START_TIME" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 运行时间段工作流
# 使用新的项目结构路径
# --skip-send 参数可以取消注释，如果只想生成报告文件而不发送
python3 workflows/period_workflow.py --start-date "$LAST_WEEK_START" --end-date "$LAST_WEEK_END" 2>&1 | tee -a "$LOG_FILE"

# 如果不想发送到飞书，只生成报告文件，使用下面的命令：
# python3 workflows/period_workflow.py --start-date "$LAST_WEEK_START" --end-date "$LAST_WEEK_END" --skip-send 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

END_TIME=$(date)

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 周报生成任务执行成功" | tee -a "$LOG_FILE"
    echo "📊 周报时间段: $LAST_WEEK_START 至 $LAST_WEEK_END" | tee -a "$LOG_FILE"
else
    echo "❌ 周报生成任务执行失败，错误码: $EXIT_CODE" | tee -a "$LOG_FILE"
fi
echo "结束时间: $END_TIME" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
