#!/bin/sh
# Run on the CPN host. Daily cron example is separate and is NOT installed here.
set -eu
: "${CPN_SEED_ROOT:?Set the absolute application directory}"
mkdir -p "$CPN_SEED_ROOT/private"
exec 9>"$CPN_SEED_ROOT/private/update.lock"
flock -n 9 || exit 0
cd "$CPN_SEED_ROOT"
# Downloads the full official EPA APPRIL workbook each run, then reconciles.
# Optional authorized enrichment: GREENBOOK_FEED_URL and CDMS_FEED_URL.
# Optional state evidence: STATE_REGISTRATION_FEED_URL (see STATE_REGISTRATIONS.md).
python3 refresh_epa.py
