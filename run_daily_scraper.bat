@echo off
REM 每天定时运行爬虫程序，爬取前一天的数据

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 激活虚拟环境（如果使用虚拟环境）
REM 如果使用虚拟环境，取消下面这行的注释并修改路径
REM call .venv\Scripts\activate

REM 运行爬虫程序，爬取昨天的数据（days-ago=1）
echo ========================================
echo 开始执行每日爬虫任务
echo 目标: 爬取昨天的数据
echo 时间: %date% %time%
echo ========================================
echo.

python CompetitorDailyScraperFromDB.py --days-ago 1

REM 检查执行结果
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo 爬虫任务执行成功
    echo ========================================
) else (
    echo.
    echo ========================================
    echo 爬虫任务执行失败，错误码: %errorlevel%
    echo ========================================
)

REM 保持窗口打开（可选，用于调试）
REM pause

exit %errorlevel%
