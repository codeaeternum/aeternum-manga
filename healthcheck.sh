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
check "ManhwaWeb API"     "https://api.manhwaweb.com/manhwa/nuevos" 200

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

# ---------- imágenes CDN (una portada real por fuente) ----------
# Cada CDN tiene su política de Referer: lectortmo lo PROHIBE, webtoons/manhwaweb lo EXIGEN.
img_check() { # name, list_url, referer(""=none), url_regex
  local name="$1" url="$2" ref="$3" rx="$4" img code
  img=$(curl -sL --max-time 20 -A "$UA" "$url" \
        | grep -oE "$rx" | head -1 | sed 's|\\/|/|g')
  [[ -n "$img" ]] || { FAILURES+=("$name: no se extrajo URL de imagen"); return; }
  if [[ -n "$ref" ]]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -A "$UA" -e "$ref" "$img")
  else
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -A "$UA" "$img")
  fi
  [[ "$code" == "200" ]] || FAILURES+=("$name CDN: HTTP $code — $img")
}

img_check "LectorTMOo img"    "https://lectortmo.online/api/mangas?page=1"  ""                            'https:\\/\\/cdn\.lectortmoo\.com[^"]+'
img_check "TuMangaHentai img" "https://tumangahentai.com/api/mangas?page=1" ""                            'https:\\/\\/cdn\.tmohentaii\.com[^"]+'
img_check "ManhwaWeb img"     "https://api.manhwaweb.com/manhwa/nuevos"     "https://manhwaweb.com/"      'https://img[0-9]mw\.xyz[^"]+'
# LeerCapitulo: covers son rutas relativas /covers/... en el dominio principal
LC_IMG=$(curl -sL --max-time 20 -A "$UA" "https://www.leercapitulo.co/" \
  | grep -oE 'src="/covers/[^"]+\.(jpg|webp|png)[^"]*"' | head -1 | cut -d'"' -f2)
if [[ -z "$LC_IMG" ]]; then
  FAILURES+=("LeerCapitulo img: no se extrajo URL")
else
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -A "$UA" "https://www.leercapitulo.co$LC_IMG")
  [[ "$code" == "200" ]] || FAILURES+=("LeerCapitulo CDN: HTTP $code — $LC_IMG")
fi
img_check "HentaiMode img"    "https://hentaimode.com/"                     ""                            'https://[a-z0-9.-]*kmcdn\.top[^"]+'
img_check "Webtoons img"      "https://www.webtoons.com/es/ranking/trending" "https://www.webtoons.com/"  'https://webtoon-phinf\.pstatic\.net[^"]+'

# NovelCool: el listado es POST con credenciales de la app
NC_IMG=$(curl -s --max-time 20 -A "$UA" -X POST "https://api.novelcool.com/elite/hot/" \
  -H "Content-Type: application/json" \
  -d '{"appId":"202201290625004","secret":"c73a8590641781f203660afca1d37ada","lang":"es"}' \
  | grep -oE 'https:\\/\\/img\.novelcool\.com[^"]+' | head -1 | sed 's|\\/|/|g')
if [[ -z "$NC_IMG" ]]; then
  FAILURES+=("NovelCool img: no se extrajo URL")
else
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -A "$UA" "$NC_IMG")
  [[ "$code" == "200" ]] || FAILURES+=("NovelCool CDN: HTTP $code — $NC_IMG")
fi

if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "OK — las 8 fuentes responden"
  exit 0
fi
printf '%s\n' "FALLOS (${#FAILURES[@]}):" "${FAILURES[@]}"
exit 1
