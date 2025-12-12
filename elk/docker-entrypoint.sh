#!/bin/bash
# Entrypoint script để tự động setup keystore nếu có SMTP_PASSWORD

set -e

if [ -n "$SMTP_PASSWORD" ]; then
    KEYSTORE_PATH="/usr/share/elasticsearch/config/elasticsearch.keystore"
    
    # Tạo keystore nếu chưa tồn tại
    if [ ! -f "$KEYSTORE_PATH" ]; then
        echo "Creating Elasticsearch keystore..."
        /usr/share/elasticsearch/bin/elasticsearch-keystore create
    fi
    
    if /usr/share/elasticsearch/bin/elasticsearch-keystore list | grep -q "xpack.notification.email.account.gmail_account.smtp.secure_password"; then
        echo "Updating existing SMTP password in keystore..."
        # Xóa entry cũ và thêm lại
        echo "$SMTP_PASSWORD" | /usr/share/elasticsearch/bin/elasticsearch-keystore add \
            xpack.notification.email.account.gmail_account.smtp.secure_password \
            --stdin --force
    else
        echo "Adding SMTP password to keystore..."
        echo "$SMTP_PASSWORD" | /usr/share/elasticsearch/bin/elasticsearch-keystore add \
            xpack.notification.email.account.gmail_account.smtp.secure_password \
            --stdin
    fi
    
    echo "✓ SMTP password đã được cấu hình an toàn trong keystore"
fi

# Chạy entrypoint mặc định của Elasticsearch
# Elasticsearch 7.17.5 sử dụng entrypoint tại /usr/local/bin/docker-entrypoint.sh
if [ -f "/usr/local/bin/docker-entrypoint.sh" ]; then
    exec /usr/local/bin/docker-entrypoint.sh "$@"
else
    # Fallback: chạy elasticsearch trực tiếp
    exec /usr/share/elasticsearch/bin/elasticsearch "$@"
fi

