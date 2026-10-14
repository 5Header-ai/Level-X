#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out="$src/../../../build/MetalProbe.app"
sdk=$(xcrun --sdk iphoneos --show-sdk-path)
mkdir -p "$out"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$sdk" \
    -miphoneos-version-min=14.0 -fobjc-arc -fmodules -Wall -Wextra \
    -Wno-unused-parameter -framework UIKit -framework Foundation -framework Metal \
    "$src/MetalProbe.m" -o "$out/MetalProbe"
cp "$src/Info.plist" "$out/Info.plist"
plutil -lint "$out/Info.plist"
printf 'Unsigned diagnostic app: %s\n' "$out"
