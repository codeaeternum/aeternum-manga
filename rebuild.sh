#!/usr/bin/env bash
# Recompila todas las extensiones y regenera el repo (index.pb + index.min.json + APK/JAR).
# Sincroniza los módulos propios (patches/modules/) dentro del árbol fuente antes de compilar.
# Uso: ./rebuild.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$HERE/../extensions-source"

export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME="$HOME/Library/Android/sdk"
export KEY_STORE_PASSWORD=tachimanga-repo
export ALIAS=repo
export KEY_PASSWORD=tachimanga-repo

# Módulos propios vendored -> sustituyen al módulo upstream del mismo nombre
for d in "$HERE"/patches/modules/*/*/; do
  rel="${d#"$HERE"/patches/modules/}"
  rm -rf "$SRC_DIR/src/$rel"
done
cp -R "$HERE"/patches/modules/* "$SRC_DIR/src/"

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
for m in "${MODULES[@]}"; do
  TASKS+=(":src:$m:assembleRelease")
done

cd "$SRC_DIR"
./gradlew "${TASKS[@]}" --console=plain

cd "$HERE"
python3 build-repo.py
