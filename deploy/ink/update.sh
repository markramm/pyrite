#!/bin/bash
# Pull latest code and redeploy pyrite.ink
# Run as the deploy user: bash ~/pyrite/deploy/ink/update.sh
set -e

cd ~/pyrite
git pull
docker compose -f deploy/ink/docker-compose.yml up -d --build
echo "Updated and restarted."
