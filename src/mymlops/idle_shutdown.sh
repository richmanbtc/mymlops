#!/bin/bash

# ログファイルのパスを設定
LOGFILE="/var/log/idle_shutdown.log"

# アイドル時間の上限 (秒単位、ここでは 300秒 = 5分) を設定
IDLE_TIMEOUT=3600

# 最後のアクティブ時間を保持する変数
last_active=$(date +%s)

# システムのCPU使用率をチェックしてアイドルかどうかを判定する関数
check_idle() {
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "$(date): Current CPU Usage: ${cpu_usage}%" >> "$LOGFILE"
    if (( $(echo "$cpu_usage < 5" | bc -l) )); then
        return 0
    else
        return 1
    fi
}

# 監視を続けるループを開始
echo "$(date): Starting idle shutdown monitor." >> "$LOGFILE"

while true; do
    if check_idle; then
        current_time=$(date +%s)
        idle_duration=$((current_time - last_active))

        if (( idle_duration >= IDLE_TIMEOUT )); then
            echo "$(date): System idle for $IDLE_TIMEOUT seconds, shutting down..." >> "$LOGFILE"
            shutdown -h now
            exit 0
        fi
    else
        last_active=$(date +%s)
    fi

    # チェック間隔を10秒ごとに設定
    sleep 10
done
