# Aeternum Manga

Repo personal de extensiones para Tachimanga con **scrapers propios** —
las 7 extensiones están escritas y mantenidas aquí (en `patches/modules/`),
iOS-nativas desde cero. El framework de build (`KeiSource`, extension-lib,
plugin Gradle) viene de [`keiyoushi/extensions-source`](https://github.com/keiyoushi/extensions-source)
**congelado en un commit fijo** — solo como toolchain, no como fuente de scrapers.

Sirve **dos formatos** de índice:

- `index.pb` — formato nuevo (protobuf); incluye `jarUrl` por extensión.
  **Es el que hay que usar en Tachimanga/iOS**: la app corre bytecode JVM y
  descarga el `.jar`, no el `.apk`.
- `index.min.json` — formato legado (solo APKs; para forks Android tipo Mihon).

## Añadir en Tachimanga

1. En Tachimanga: **More → Extensions → Extension Repositories → Add Repository**
2. Pega la URL del `index.pb`:

   ```
   https://raw.githubusercontent.com/codeaeternum/aeternum-manga/main/index.pb
   ```

3. **Browse → Extensions** → instala las que necesites.

> Las extensiones van firmadas con un keystore propio. Si ya tenías instalada
> una versión firmada por este repo, las updates llegan solas.

## Extensiones incluidas

| Extensión | Idioma | Fuentes | Notas |
|---|---|---|---|
| ManhwaWeb | es | 1 | API JSON propia |
| Ikigai Mangas | es | 1 | Dominio autodescubierto por request (rota); sin búsqueda por texto — el sitio la hace vía JS/Qwik, imposible sin WebView |
| LeerCapitulo | es | 1 | Con filtros de género/tipo/estado + URL search |
| HentaiMode | es | 1 | NSFW; búsqueda por nombre vía etiquetas/series/artistas (la del sitio está rota) |
| NovelCool | en, es, de, ru, it, pt-BR, fr | 7 | API app, URL search, capítulos de texto omitidos |
| Webtoons.com | en, es, id, th, fr, zh-Hant, de | 7 | Búsqueda Originales/Canvas paginada; sin author notes ni selector de calidad |
| LectorTMOo | es | 2 | lectortmo.online + tumangahentai.com (NSFW), géneros dinámicos |

## Estructura

```
patches/modules/<lang>/<ext>/   ← código fuente propio de cada extensión
build-repo.py                   ← genera index.pb + index.min.json + apk/ + jar/
rebuild.sh                      ← sync módulos → compila → regenera repo
healthcheck.sh                  ← verifica endpoints de las 8 fuentes
.github/workflows/
  rebuild.yml                   ← semanal: compila todo desde framework pinned
  healthcheck.yml               ← diario: ping a fuentes, abre issue si caen
```

## Recompilar local

```bash
./rebuild.sh   # hace todo: sync módulos → gradle → índices
```

Las extensiones redirigen `buildDir` a `~/.aeternum-ext-build/` porque ProGuard
(task `createReleaseExtensionJar`) no tolera espacios en la ruta del checkout.

Requiere: JDK 17 (`brew install openjdk@17`), Android SDK, y `signingkey.jks`
en la raíz de `extensions-source` (env: `KEY_STORE_PASSWORD`, `ALIAS`,
`KEY_PASSWORD`).

## Notas

- `repo.json`/`index.pb` llevan la huella SHA-256 del certificado de firma;
  Tachimanga la usa para verificar los `.jar`/`.apk`.
- Todas las extensiones son iOS/OpenJ9-safe por diseño: cero `android.*`,
  sin `SharedPreferences`/`WebView`/`CookieManager`/prefs screens.
- Al cambiar un scraper, sube su `versionCode` en `build.gradle.kts` para que
  la app lo vea como update.
