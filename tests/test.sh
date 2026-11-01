#!/bin/bash
set -euo pipefail

# Run local core and regression checks before the network-dependent acceptance test.
for test in test_core.py test_regression.py test_acceptance.py; do
    docker compose exec -T iris irispython "/home/irisowner/dev/tests/$test"
done

# Check the ObjectScript health status without relying on error text.
result=$(docker compose exec -T iris iris session IRIS -U USER <<'IRISEOF'
set r = ##class(dc.hfloader.Loader).Health()
if $system.Status.IsOK(r) write "HEALTH_OK",!
halt
IRISEOF
)
printf '%s\n' "$result"
[[ "$result" == *HEALTH_OK* ]]
