# Contribuir a Aeternum Manga

Las extensiones de este repo son **scrapers propios** escritos para
Tachimanga/iOS (runtime OpenJ9). Viven en `patches/modules/<lang>/<ext>/`
y se copian sobre el árbol de `keiyoushi/extensions-source` al compilar —
ese árbol es **solo toolchain** (congelado en commit `8c3323cc`), nunca
modifiques archivos fuera del módulo vendored.

## Reglas duras iOS/OpenJ9

El runtime de Tachimanga ejecuta el JAR sobre JVM con stubs parciales de
`android.*`. Un método cuya **firma** referencie una clase inexistente rompe
la verificación de TODA la extensión (`JVMVRFY021` / VerifyError).

Prohibido en código de extensión:

- `android.*` / `androidx.*` en general
- `SharedPreferences`, `ConfigurableSource`, `PreferenceScreen`,
  `*PreferenceCompat` — no hay UI de preferencias en iOS
- `android.webkit.*` (`CookieManager`, `WebView`, `runWebView`)
- `android.graphics.*`, `android.widget.*`
- `android.util.Log`
- `lib:textinterceptor`

Alternativas:

| En vez de... | Usa... |
|---|---|
| Preferencias/mirror de dominio | Valor en memoria con re-descubrimiento (ver `ikigaimangas`) |
| `CookieManager` | Header `Cookie`/`Referer` via interceptor OkHttp (ver `webtoons`) |
| Interceptor de texto | Devolver capítulo vacío + nota en el nombre (ver novelas NovelCool) |

## Convenciones de código (mismas que keiyoushi)

- `@Source class X : KeiSource()` — nunca `HttpSource` directo.
- Metadata (`name`/`lang`/`baseUrl`/`versionId`) **solo** en el bloque
  `source {}` de `build.gradle.kts`. KSP la inyecta — no declares esos
  `val` en la clase.
- Múltiples fuentes = múltiples bloques `source {}` (no `SourceFactory`).
- DTOs `@Serializable`: `class` normal (NO `data class`), campos `private`
  cuando se pueda, `@SerialName` solo si la clave JSON difiere.
- Sin `Json` locales: usa `response.parseAs<T>()`,
  `parseAsProto<T>()`, `asJsoup()`, `keiyoushi.network.get`.
- Rate-limit por host cuando el sitio lo amerite (`rateLimit(...)`).
- `build.gradle.kts` debe terminar con:

  ```kotlin
  layout.buildDirectory.set(file(System.getProperty("user.home") + "/.aeternum-ext-build/${project.path.replace(':', '_')}"))
  ```

  (ProGuard revienta con espacios en la ruta del checkout.)

## Versionado — no toques `versionCode`

`version-bump.py` lo sube automáticamente cuando el contenido del módulo
cambia (hash en `versions.json`). Bajarlo o repetirlo rompe el update en
la app; subirlo a mano está bien solo para el release inicial.

**Excepción**: si cambias `name`/`lang`/`versionId` de un `source {}`
cambia el ID generado → los usuarios pierden sus bibliotecas. Solo hazlo
si la fuente es nueva.

## Flujo

```bash
./rebuild.sh          # bump → sync módulos → gradle assembleRelease → índices
./healthcheck.sh      # ping endpoints + una imagen CDN real por fuente
git add -A && git commit && git push
```

CI (`rebuild.yml`) hace lo mismo semanal desde upstream pinned;
`healthcheck.yml` corre diario y abre issue si algo cae;
`framework-watch.yml` avisa mensual si el toolchain upstream diverge del pin.

## Añadir una fuente nueva

1. `mkdir patches/modules/<lang>/<nombre>` con `build.gradle.kts` +
   `src/eu/kanade/tachiyomi/extension/<lang>/<nombre>/`.
2. Copia el `build.gradle.kts` de `es/leercapitulo` como plantilla
   (cambia name/lang/baseUrl/source{}/deeplink{}).
3. Iconos: `res/mipmap-*/ic_launcher.png` (mipmap-xhdpi mínimo para `icon/`).
4. Agrega `<lang>:<nombre>` a `MODULES` en `rebuild.sh` y al gradle
   task list de `rebuild.yml`.
5. Agrega un check a `healthcheck.sh`.
6. `./rebuild.sh` → revisa que aparezca en `index.min.json`.
