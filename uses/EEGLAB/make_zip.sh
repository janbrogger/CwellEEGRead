#!/usr/bin/env bash
# Build the EEGLAB plugin zip: dist/cadwellio<version>.zip with the versioned
# folder at the zip root (what the EEGLAB plugin manager and manual install expect).
set -euo pipefail
cd "$(dirname "$0")"
VERSION=$(sed -n "s/.*vers = 'cadwellio\([0-9.]*\)'.*/\1/p" cadwellio/eegplugin_cadwellio.m)
[ -n "$VERSION" ] || { echo "could not read version from eegplugin_cadwellio.m" >&2; exit 1; }
NAME="cadwellio$VERSION"
rm -rf "dist/$NAME" && mkdir -p "dist/$NAME"
cp cadwellio/*.m cadwellio/README.md cadwellio/LICENSE "dist/$NAME/"
# The plugin reads SQLite natively (cadwell_sqlite_native.m); the optional
# JDBC cross-check backend is only bundled on request: ./make_zip.sh --with-jdbc
if [ "${1:-}" = "--with-jdbc" ] && ls cadwellio/lib/sqlite-jdbc*.jar >/dev/null 2>&1; then
    mkdir -p "dist/$NAME/lib" && cp cadwellio/lib/sqlite-jdbc*.jar "dist/$NAME/lib/"
fi
( cd dist && rm -f "$NAME.zip" && zip -qr "$NAME.zip" "$NAME" )
echo "built dist/$NAME.zip"
