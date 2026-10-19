#!/bin/bash
# Builds the Rust writing engine as ios/Engine/ParzrEngine.xcframework (iOS device + Apple-silicon
# simulator), rules-only (no native model runtime). Needs rustup with the aarch64-apple-ios and
# aarch64-apple-ios-sim targets (`rustup target add aarch64-apple-ios aarch64-apple-ios-sim`) and
# full Xcode (set DEVELOPER_DIR when xcode-select points at the Command Line Tools).
#
#   ios/scripts/build-engine-xcframework.sh            # release build
#   PARZR_JOBS=2 ios/scripts/build-engine-xcframework.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/ios/Engine"
JOBS="${PARZR_JOBS:-2}"
export PATH="$HOME/.cargo/bin:$PATH"
if [[ -z "${DEVELOPER_DIR:-}" && "$(xcode-select -p)" == /Library/Developer/CommandLineTools* ]]; then
    export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
fi
export IPHONEOS_DEPLOYMENT_TARGET="${IPHONEOS_DEPLOYMENT_TARGET:-26.0}"

for target in aarch64-apple-ios aarch64-apple-ios-sim; do
    rustup target list --installed | grep -qx "$target" || rustup target add "$target"
    echo "Building engine for $target"
    # Only the static library: the crate's cdylib and binaries are not needed on iOS.
    nice -n 15 cargo rustc --manifest-path "$ROOT/engine/Cargo.toml" --release --locked \
        --no-default-features --lib --crate-type staticlib --target "$target" -j "$JOBS"
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
for target in aarch64-apple-ios aarch64-apple-ios-sim; do
    mkdir -p "$STAGE/$target/include"
    cp "$OUT/include/parzr_engine.h" "$OUT/include/module.modulemap" "$STAGE/$target/include/"
    # Not stripped: stripping local symbols from a static archive's objects can break their
    # relocations. The app's own link strips what it does not use.
    cp "$ROOT/engine/target/$target/release/libparzr_engine.a" "$STAGE/$target/libparzr_engine.a"
done

rm -rf "$OUT/ParzrEngine.xcframework"
xcodebuild -create-xcframework \
    -library "$STAGE/aarch64-apple-ios/libparzr_engine.a" -headers "$STAGE/aarch64-apple-ios/include" \
    -library "$STAGE/aarch64-apple-ios-sim/libparzr_engine.a" -headers "$STAGE/aarch64-apple-ios-sim/include" \
    -output "$OUT/ParzrEngine.xcframework"
du -sh "$OUT/ParzrEngine.xcframework"/*/libparzr_engine.a
