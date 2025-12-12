#!/bin/bash
# Script để setup Elasticsearch keystore cho SMTP password
# Sử dụng: ./setup_keystore.sh <password>

set -e

PASSWORD="${1:-}"

if [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <smtp_password>"
    echo "Hoặc set environment variable: SMTP_PASSWORD=<password> $0"
    exit 1
fi

# Đường dẫn đến keystore
KEYSTORE_PATH="/usr/share/elasticsearch/config/elasticsearch.keystore"

# Tạo keystore nếu chưa tồn tại
if [ ! -f "$KEYSTORE_PATH" ]; then
    echo "Creating Elasticsearch keystore..."
    /usr/share/elasticsearch/bin/elasticsearch-keystore create
fi

# Thêm hoặc cập nhật password
echo "Adding SMTP password to keystore..."
echo "$PASSWORD" | /usr/share/elasticsearch/bin/elasticsearch-keystore add \
    xpack.notification.email.account.gmail_account.smtp.secure_password \
    --stdin

echo "✓ SMTP password đã được thêm vào keystore an toàn"
echo "✓ Keystore location: $KEYSTORE_PATH"


