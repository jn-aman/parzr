#!/bin/bash
# Builds Parzr for iOS from the command line, unsigned, for the simulator:
#   1. the Rust engine XCFramework (skipped when present; PARZR_REBUILD_ENGINE=1 forces it),
#   2. the Xcode project (xcodegen),
#   3. xcodebuild build (or `test` when called as `build.sh test`).
#
#   ios/scripts/build.sh            # build app + keyboard for the simulator
#   ios/scripts/build.sh test       # also run ParzrKitTests on a simulator
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IOS="$ROOT/ios"
ACTION="${1:-build}"
if [[ -z "${DEVELOPER_DIR:-}" && "$(xcode-select -p)" == /Library/Developer/CommandLineTools* ]]; then
    export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
fi

if [[ ! -d "$IOS/Engine/ParzrEngine.xcframework" || "${PARZR_REBUILD_ENGINE:-0}" == 1 ]]; then
    "$IOS/scripts/build-engine-xcframework.sh"
fi
(cd "$IOS" && xcodegen generate --quiet)

DESTINATION="${PARZR_DESTINATION:-}"
if [[ -z "$DESTINATION" ]]; then
    if [[ "$ACTION" == test ]]; then
        # Any available iPhone simulator.
        DEVICE=$(xcrun simctl list devices available | grep -E '^\s+iPhone' | head -1 | sed -E 's/.*\(([0-9A-F-]{36})\).*/\1/')
        DESTINATION="id=$DEVICE"
    else
        DESTINATION="generic/platform=iOS Simulator"
    fi
fi

status=0
nice -n 15 xcodebuild -project "$IOS/Parzr.xcodeproj" -scheme Parzr \
    -destination "$DESTINATION" -derivedDataPath "$IOS/build" \
    -jobs "${PARZR_JOBS:-2}" CODE_SIGNING_ALLOWED=NO "$ACTION" || status=$?
# Do not leave the test simulator running (its media daemons keep the CPU busy).
if [[ "$ACTION" == test && -n "${DEVICE:-}" ]]; then xcrun simctl shutdown "$DEVICE" 2>/dev/null || true; fi
exit $status
