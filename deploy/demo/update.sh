#!/bin/bash
# Pull latest code and redeploy the demo site
# Run as the deploy user: bash ~/pyrite/deploy/demo/update.sh
set -e

cd ~/pyrite
git pull

cd ~/pyrite-kb-demo
git pull

cd ~/pyrite
docker compose -f deploy/demo/docker-compose.yml up -d --build
echo "Updated and restarted."
