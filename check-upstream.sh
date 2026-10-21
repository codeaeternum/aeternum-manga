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
echo "==> git fetch origin main"
git fetch -q origin main || { echo "ERROR: fetch falló (¿sin red?)" >&2; exit 1; }

# Clone shallow: no hay merge-base. HEAD..origin/main ya es "lo que ellos
# tienen y nosotros no". Los commits-frontera del graft (sin padre en el
# object store) aparecen como si tocaran TODOS los archivos — hay que
# excluirlos o ensucian cada módulo.
BOUNDARY=$(git rev-list --max-parents=0 --abbrev-commit origin/main | tr '\n' ' ')

echo "HEAD del fork:   $(git log --oneline -1 HEAD | cut -c1-70)"
echo "origin/main:     $(git log --oneline -1 origin/main | cut -c1-70)"
echo

# Módulos publicados (los que rebuild.sh compila -> aeternum-manga/jar)
MODULES=(
    es:manhwaweb es:hentaimode es:ikigaimangas es:leercapitulo es:lectortmoo
    all:mangaplus all:novelcool all:webtoons
)

TOTAL=0
for rel in "${MODULES[@]}"; do
    dir="src/${rel/://}"
    # Commits upstream que tocan el módulo, menos los graft-boundary
    lines=$(git log --oneline HEAD..origin/main -- "$dir" | { grep -vF -f <(printf '%s\n' $BOUNDARY) || true; })
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
