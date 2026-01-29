#!/bin/bash

# 1. 环境与路径设置
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# 动态获取脚本所在目录作为项目根目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$PROJECT_DIR/data/archive.db"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_TIME=$(date +"%Y-%m-%d %H:%M:%S")
BACKUP_FILE="yipai_archive_data_$TIMESTAMP.tar.gz"
RCLONE_REMOTE="keep-yipai-me:keep-yipai-me"

# 2. 数据库瘦身
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" "VACUUM;"
else
    echo "[$LOG_TIME] 警告: 数据库文件不存在: $DB_PATH"
fi

# 3. 核心数据打包
# 仅备份 data/ 目录(含数据库和媒体文件) 以及 配置文件(config.py, .env)
mkdir -p "$BACKUP_DIR"

# 构建要备份的文件列表，仅包含存在的文件
FILES_TO_BACKUP="data"
[ -f "$PROJECT_DIR/config.py" ] && FILES_TO_BACKUP="$FILES_TO_BACKUP config.py"
[ -f "$PROJECT_DIR/.env" ] && FILES_TO_BACKUP="$FILES_TO_BACKUP .env"

# 使用 -C 切换目录，确保压缩包内路径相对于是项目根目录
tar -czvf "$BACKUP_DIR/$BACKUP_FILE" -C "$PROJECT_DIR" $FILES_TO_BACKUP

# 4. 同步到 R2
if [ $? -eq 0 ]; then
    echo "[$LOG_TIME] 打包成功: $BACKUP_FILE"
    # 检查 rclone 是否安装
    if command -v rclone &> /dev/null; then
        rclone copy "$BACKUP_DIR/$BACKUP_FILE" "$RCLONE_REMOTE" --s3-no-check-bucket
        if [ $? -eq 0 ]; then
             echo "[$LOG_TIME] 同步成功"
        else
             echo "[$LOG_TIME] 同步失败"
             exit 1
        fi
    else
        echo "[$LOG_TIME] 未找到 rclone，跳过同步"
    fi
else
    echo "[$LOG_TIME] 打包失败"
    exit 1
fi

# 5. 本地滚动清理 (保留3天)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +3 -delete