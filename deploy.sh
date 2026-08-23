#!/usr/bin/env bash
set -e

TARGET_HOST="${1}"
if [ -z "${TARGET_HOST}" ]; then
    echo "Usage: ./deploy.sh <target-host> (e.g. ./deploy.sh localhost or ./deploy.sh user@mediaserver)"
    exit 1
fi
TARGET_DIR="~/40hoursaday"

echo "🚀 Deploying 40hoursaday to ${TARGET_HOST}:${TARGET_DIR}..."

# Create target directory
ssh "${TARGET_HOST}" "mkdir -p ${TARGET_DIR}/midi_files ${TARGET_DIR}/static ~/.config/systemd/user"

# Sync files
rsync -avz --exclude '.git' --exclude '__pycache__' ./ "${TARGET_HOST}:${TARGET_DIR}/"

# Install systemd service
ssh "${TARGET_HOST}" "
    cp ${TARGET_DIR}/systemd/40hoursaday.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable 40hoursaday.service
    systemctl --user restart 40hoursaday.service
"

echo "✅ Successfully deployed & started on http://${TARGET_HOST}:8090"
