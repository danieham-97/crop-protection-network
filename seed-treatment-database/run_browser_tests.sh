#!/usr/bin/env bash
# Use the matching prebuilt browser image; do not install OS packages on each run.
set -euo pipefail
SEED_APP_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SEED_PLAYWRIGHT_VERSION=1.62.1
SEED_BROWSER_IMAGE="mcr.microsoft.com/playwright:v${SEED_PLAYWRIGHT_VERSION}-noble"

cd "$SEED_APP_ROOT"
npm install --no-save --package-lock=false "playwright@${SEED_PLAYWRIGHT_VERSION}"
# Retry image acquisition only. A failing browser test must fail the job.
for attempt in 1 2 3; do
  if docker pull "$SEED_BROWSER_IMAGE"; then break; fi
  if [ "$attempt" -eq 3 ]; then exit 1; fi
  sleep 10
done

docker run --rm --init --ipc=host \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp --env CI=true \
  --volume "$SEED_APP_ROOT:/work" --workdir /work \
  "$SEED_BROWSER_IMAGE" node tests/ui_test.cjs
