#!/usr/bin/env bash
set -euo pipefail

# GitHub Actions supplies the full image address as the first argument.
APP_IMAGE="${1:?An image address is required}"
export APP_IMAGE

AWS_REGION="ap-south-1"
REGISTRY="458013564538.dkr.ecr.ap-south-1.amazonaws.com"
APP_DIR="/opt/employee-assistant"

# Create the deployment directory.
mkdir -p "$APP_DIR/database"
cd "$APP_DIR"

# Authenticate Docker and download the application image.
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$REGISTRY"

docker pull "$APP_IMAGE"

# Create a temporary container to copy deployment files from the image.
FILE_CONTAINER=$(docker create "$APP_IMAGE")
trap 'docker rm "$FILE_CONTAINER" >/dev/null 2>&1 || true' EXIT

docker cp "$FILE_CONTAINER:/app/docker-compose.yml" ./docker-compose.yml
docker cp "$FILE_CONTAINER:/app/compose.aws.yml" ./compose.aws.yml
docker cp "$FILE_CONTAINER:/app/database/init.sql" ./database/init.sql

# Read encrypted settings into a file accessible only to its owner.
umask 077

aws ssm get-parameter \
  --region "$AWS_REGION" \
  --name "/employee-assistant/app-env" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text > .env.next

# Remember which application image this deployment uses.
printf '\nAPP_IMAGE=%s\n' "$APP_IMAGE" >> .env.next
chmod 600 .env.next
mv .env.next .env

# Validate configuration without printing passwords.
docker compose -f docker-compose.yml -f compose.aws.yml config --quiet

# Download the database images and start the application.
docker compose -f docker-compose.yml -f compose.aws.yml pull

docker compose -f docker-compose.yml -f compose.aws.yml \
  up -d --no-build --wait --wait-timeout 1200

# Check the API and frontend.
curl --fail --silent --show-error \
  --retry 12 --retry-connrefused --retry-delay 5 --max-time 10 \
  http://127.0.0.1:8000/health

curl --fail --silent --show-error \
  --retry 12 --retry-connrefused --retry-delay 5 --max-time 10 \
  http://127.0.0.1:8501/_stcore/health

docker compose -f docker-compose.yml -f compose.aws.yml ps

echo "Deployment completed successfully."