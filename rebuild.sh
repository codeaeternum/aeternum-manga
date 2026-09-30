#!/usr/bin/env bash
# Recompila todas las extensiones y regenera el repo (index.min.json + APKs).
# Uso: ./rebuild.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$HERE/../extensions-source"

export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME="$HOME/Library/Android/sdk"
export KEY_STORE_PASSWORD=tachimanga-repo
export ALIAS=repo
export KEY_PASSWORD=tachimanga-repo

MODULES=(
  es:manhwaweb
  es:hentaimode
  es:ikigaimangas
  es:leercapitulo
  es:lectortmoo
  all:novelcool
  all:webtoons
)

TASKS=()
EXCLUDES=()
for m in "${MODULES[@]}"; do
  TASKS+=(":src:$m:assembleRelease")
  # Los tasks .jar no los usa Tachimanga y fallan si la ruta tiene espacios
  EXCLUDES+=(-x ":src:$m:createReleaseExtensionJar" -x ":src:$m:signReleaseExtensionJar")
done

cd "$SRC_DIR"
./gradlew "${TASKS[@]}" "${EXCLUDES[@]}" --console=plain

cd "$HERE"
python3 build-repo.py
