# Aeternum Manga

Repo personal de extensiones para Tachimanga, compilada desde
[`keiyoushi/extensions-source`](https://github.com/keiyoushi/extensions-source)
con firma propia.

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

| Extensión | Idioma | Estado |
|---|---|---|
| ManhwaWeb | es | OK |
| Ikigai Mangas | es | Sin búsqueda por texto (el sitio la hace vía JS/Qwik) |
| LeerCapitulo | es | OK |
| HentaiMode | es | NSFW; búsqueda rota en el sitio, no en la ext |
| NovelCool | en, es, de, ru, it, pt-BR, fr | OK |
| Webtoons.com | en, es, id, th, fr, zh-Hant, de | Sin author notes ni selector de calidad |
| LectorTMOo | es | Propia (lectortmo.online) |
| TuMangaHentai | es | Propia (tumangahentai.com), NSFW |

## Recompilar y regenerar

```bash
cd ../extensions-source
./gradlew :src:es:lectortmoo:assembleRelease   # genera apk + jar firmados
cd ../aeternum-manga
python3 build-repo.py                          # copia artefactos + índices
```

Las extensiones redirigen `buildDir` a `~/.aeternum-ext-build/` porque ProGuard
(task `createReleaseExtensionJar`) no tolera espacios en la ruta del checkout.

Requiere: JDK 17 (`brew install openjdk@17`), Android SDK, y `signingkey.jks`
en la raíz de `extensions-source` (env: `KEY_STORE_PASSWORD`, `ALIAS`,
`KEY_PASSWORD`).

## Notas

- `repo.json`/`index.pb` llevan la huella SHA-256 del certificado de firma;
  Tachimanga la usa para verificar los `.jar`/`.apk`.
- Extensiones muertas (TMO, cerrado por la Policía Nacional abr-2026) están
  excluidas vía `SKIP_MODULES` en `build-repo.py`.
