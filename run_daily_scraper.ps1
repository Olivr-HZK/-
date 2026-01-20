# PowerShell脚本：每天定时运行爬虫程序
# 用于Windows任务计划程序

# 切换到脚本所在目录
Set-Location $PSScriptRoot

# 激活虚拟环境（如果使用虚拟环境）
# 如果使用虚拟环境，取消下面这行的注释
# & .\.venv\Scripts\Activate.ps1

# 日志文件路径
$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$logFile = Join-Path $logDir "daily_scraper_$(Get-Date -Format 'yyyy-MM-dd').log"

# 记录开始时间
$startTime = Get-Date
Write-Output "========================================" | Tee-Object -FilePath $logFile -Append
Write-Output "开始执行每日爬虫任务" | Tee-Object -FilePath $logFile -Append
Write-Output "目标: 爬取昨天的数据" | Tee-Object -FilePath $logFile -Append
Write-Output "时间: $startTime" | Tee-Object -FilePath $logFile -Append
Write-Output "========================================" | Tee-Object -FilePath $logFile -Append
Write-Output "" | Tee-Object -FilePath $logFile -Append

try {
    # 运行爬虫程序，爬取昨天的数据
    & python CompetitorDailyScraperFromDB.py --days-ago 1 2>&1 | Tee-Object -FilePath $logFile -Append
    
    $exitCode = $LASTEXITCODE
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Output "" | Tee-Object -FilePath $logFile -Append
    Write-Output "========================================" | Tee-Object -FilePath $logFile -Append
    if ($exitCode -eq 0) {
        Write-Output "爬虫任务执行成功" | Tee-Object -FilePath $logFile -Append
    } else {
        Write-Output "爬虫任务执行失败，错误码: $exitCode" | Tee-Object -FilePath $logFile -Append
    }
    Write-Output "执行时长: $($duration.TotalSeconds) 秒" | Tee-Object -FilePath $logFile -Append
    Write-Output "结束时间: $endTime" | Tee-Object -FilePath $logFile -Append
    Write-Output "========================================" | Tee-Object -FilePath $logFile -Append
    
    exit $exitCode
} catch {
    Write-Output "执行过程中发生异常: $_" | Tee-Object -FilePath $logFile -Append
    exit 1
}
