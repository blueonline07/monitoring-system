#!/bin/bash
# Script helper để thêm SMTP password vào keystore

set -e

CONTAINER_NAME="${1:-lab_ds-elasticsearch-1}"
PASSWORD="${2:-}"

if [ -z "$PASSWORD" ]; then
    # Đọc từ .env nếu có
    if [ -f "../.env" ]; then
        PASSWORD=$(grep "^SMTP_PASSWORD=" ../.env | cut -d'=' -f2- | sed 's/^"//;s/"$//')
    fi
    
    if [ -z "$PASSWORD" ]; then
        echo "Usage: $0 [container_name] [password]"
        echo "Hoặc set SMTP_PASSWORD trong file .env"
        exit 1
    fi
fi

echo "Thêm SMTP password vào keystore..."
echo "Container: $CONTAINER_NAME"

if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container $CONTAINER_NAME không đang chạy"
    exit 1
fi

if docker exec "$CONTAINER_NAME" bash -c "echo '$PASSWORD' | bin/elasticsearch-keystore add xpack.notification.email.account.gmail_account.smtp.secure_password --stdin --force" 2>/dev/null; then
    echo "✓ Password đã được thêm vào keystore"
    echo ""
    echo "Kiểm tra keystore:"
    docker exec "$CONTAINER_NAME" bin/elasticsearch-keystore list
    echo ""
    echo "⚠ Cần restart Elasticsearch để áp dụng thay đổi:"
    echo "   docker-compose restart elasticsearch"
else
    echo "❌ Không thể thêm password. Có thể password đã tồn tại hoặc có lỗi."
    echo "   Thử xóa password cũ trước:"
    echo "   docker exec $CONTAINER_NAME bin/elasticsearch-keystore remove xpack.notification.email.account.gmail_account.smtp.secure_password"
    exit 1
fi


