#!/usr/bin/env bash
# Health check de las fuentes — verifica que los endpoints clave respondan.
# Exit 0 = todo ok; exit 1 = alguna fuente falla (imprime resumen).
set -uo pipefail

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
FAILURES=()

check() { # name, url, expected_code, [grep-pattern]
  local name="$1" url="$2" want="$3" pat="${4:-}"
  local code body
  body=$(curl -sL --max-time 20 -A "$UA" -w '\n%{http_code}' "$url") || body=$'\n000'
  code="${body##*$'\n'}"
  if [[ "$code" != "$want" ]]; then
    FAILURES+=("$name: HTTP $code (esperado $want) — $url")
    return
  fi
  if [[ -n "$pat" ]] && ! grep -q "$pat" <<< "$body"; then
    FAILURES+=("$name: respuesta sin patrón esperado ($pat) — $url")
  fi
}

# LectorTMOo + TuMangaHentai (API propia compartida)
check "LectorTMOo API"    "https://lectortmo.online/api/mangas?page=1"   200 '"data"'
check "TuMangaHentai API" "https://tumangahentai.com/api/mangas?page=1"  200 '"data"'

# ManhwaWeb (backend Railway)
check "ManhwaWeb API"     "https://manhwawebbackend-production.up.railway.app/manhwa/nuevos" 200

# Ikigai: landing + dominio activo dinámico
IKIGAI_LANDING=$(curl -sL --max-time 20 -A "$UA" "https://ikigaimangas.com")
if ! grep -q "Ir al sitio" <<< "$IKIGAI_LANDING"; then
  FAILURES+=("Ikigai: landing sin botón 'Ir al sitio'")
else
  CHUNK=$(grep -oE 'on:click="[^"]+\.js#[^"]+"' <<< "$IKIGAI_LANDING" | head -1 | grep -oE '[^"]+\.js')
  if [[ -n "$CHUNK" ]]; then
    ACTIVE=$(curl -sL --max-time 20 -A "$UA" "https://ikigaimangas.com/build/$CHUNK" | grep -oE 'i\("https://[^"]+"' | head -1 | grep -oE 'https://[^"]+')
    if [[ -z "$ACTIVE" ]]; then
      FAILURES+=("Ikigai: no se extrajo dominio activo del chunk $CHUNK")
    else
      check "Ikigai dominio activo ($ACTIVE)" "${ACTIVE%/}/series/" 200
    fi
  fi
fi

# LeerCapitulo
check "LeerCapitulo"      "https://www.leercapitulo.co/"                 200 'lc-'

# HentaiMode
check "HentaiMode"        "https://hentaimode.com/"                      200 'book-list'

# NovelCool (API POST mínima)
NC=$(curl -s --max-time 20 -A "$UA" -X POST "https://api.novelcool.com/elite/hot/" \
  -H "Content-Type: application/json" -d '{"appId":202,"secret":"","lang":"es"}' -w '\n%{http_code}')
[[ "${NC##*$'\n'}" == "200" ]] || FAILURES+=("NovelCool API: HTTP ${NC##*$'\n'}")

# Webtoons (ranking ES)
check "Webtoons"          "https://www.webtoons.com/es/ranking/trending" 200 'webtoon_list'

if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "OK — las 8 fuentes responden"
  exit 0
fi
printf '%s\n' "FALLOS (${#FAILURES[@]}):" "${FAILURES[@]}"
exit 1
