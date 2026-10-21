#!/usr/bin/env bash
# Compara los módulos publicados contra keiyoushi upstream.
# Lista los commits de upstream que tocan cada fuente y que no tenemos
# integrados — es decir, "qué se han perdido" nuestras extensiones.
#
# Uso: ./check-upstream.sh
# Exit 0 siempre (es informativo, no un gate).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$HERE/../extensions-source"

if [[ ! -d "$SRC_DIR/.git" ]]; then
    echo "ERROR: no se encuentra extensions-source en $SRC_DIR" >&2
    exit 1
fi

cd "$SRC_DIR"
# Remote de upstream configurable: local el fork usa "origin"=keiyoushi;
# en CI el clone tiene origin=fork y keiyoushi se añade como "upstream".
UPSTREAM_REMOTE="${UPSTREAM_REMOTE:-origin}"
UPSTREAM_REF="${UPSTREAM_REF:-$UPSTREAM_REMOTE/main}"
echo "==> git fetch $UPSTREAM_REMOTE main"
git fetch -q "$UPSTREAM_REMOTE" main || { echo "ERROR: fetch falló (¿sin red?)" >&2; exit 1; }

# Clone shallow: no hay merge-base. HEAD..$UPSTREAM_REF ya es "lo que ellos
# tienen y nosotros no". Los commits-frontera del graft (sin padre en el
# object store) aparecen como si tocaran TODOS los archivos — hay que
# excluirlos o ensucian cada módulo.
BOUNDARY=$(git rev-list --max-parents=0 --abbrev-commit "$UPSTREAM_REF" | tr '\n' ' ')

echo "HEAD del fork:   $(git log --oneline -1 HEAD | cut -c1-70)"
echo "$UPSTREAM_REF: $(git log --oneline -1 "$UPSTREAM_REF" | cut -c1-70)"
echo

# Módulos publicados (los que rebuild.sh compila -> aeternum-manga/jar)
MODULES=(
    es:manhwaweb es:hentaimode es:ikigaimangas es:leercapitulo es:lectortmoo
    all:mangaplus all:novelcool all:webtoons
)

# Commits revisados y descartados a propósito (cubierto ya por un parche
# propio, refactor sin efecto, etc.) — un SHA prefijo + comentario por línea.
SKIP_FILE="$HERE/.upstream-skip"
SKIP=""
[[ -f "$SKIP_FILE" ]] && SKIP=$(grep -vE '^\s*(#|$)' "$SKIP_FILE" | awk '{print $1}')

TOTAL=0
for rel in "${MODULES[@]}"; do
    dir="src/${rel/://}"
    # Commits upstream que tocan el módulo, menos graft-boundary y skips
    lines=$(git log --oneline HEAD.."$UPSTREAM_REF" -- "$dir" \
        | { grep -vF -f <(printf '%s\n' $BOUNDARY) || true; } \
        | { [[ -n "$SKIP" ]] && grep -vF -f <(printf '%s\n' $SKIP) || cat; })
    count=0
    [[ -n "$lines" ]] && count=$(wc -l <<< "$lines" | tr -d ' ')
    if [[ "$count" -eq 0 ]]; then
        echo "  $rel — al día"
    else
        TOTAL=$((TOTAL + count))
        echo "  $rel — $count commit(s) upstream sin integrar:"
        sed 's/^/      /' <<< "$lines"
    fi
done

echo
if [[ "$TOTAL" -eq 0 ]]; then
    echo "Todo al día con upstream."
else
    echo "$TOTAL commit(s) pendientes. Revisar cada uno: si el módulo es propio"
    echo "(patches/modules/) hay que portar el cambio a mano ahí, no mergear."
fi
