# Repo de extensiones Tachimanga

Repo personal de extensiones (formato legado `index.min.json`) compilada desde
[`keiyoushi/extensions-source`](../extensions-source) con firma propia.

## Añadir en Tachimanga

1. Sube esta carpeta a un repositorio **público** de GitHub (el contenido en la raíz o en una rama).
2. En Tachimanga: **More → Extensions → Extension Repositories → Add Repository**
3. Pega la URL del `index.min.json` raw, p. ej.:

   ```
   https://raw.githubusercontent.com/<tu-usuario>/<tu-repo>/main/index.min.json
   ```

4. **Browse → Extensions** → instala las que necesites.

> Si las extensiones de Keiyoushi ya estaban instaladas con otra firma,
> desinstálalas primero — Android no permite updates con firma distinta.

## Extensiones incluidas

| Extensión | Idioma | Estado |
|---|---|---|
| ManhwaWeb | es | OK |
| Ikigai Mangas | es | OK (mirror configurable en ajustes de la source) |
| LeerCapitulo | es | OK |
| HentaiMode | es | NSFW |
| NovelCool | en, es, de, ru, it, pt-BR, fr | OK |
| Webtoons.com | en, es, id, th, fr, zh-Hant, de | OK |
| TMOHentai (unoriginal) | es | ⚠️ Sitio caído (TMO desmantelado abr-2026) |
| ZonaTMO.org (unoriginal) | es | ⚠️ Sitio caído |
| Zonatmo.to (unoriginal) | es | ⚠️ Sitio caído |

## Recompilar

```bash
./rebuild.sh
```

Requiere: JDK 17 (`brew install openjdk@17`), Android SDK con platform
`android-37.0`, y `signingkey.jks` en la raíz de `extensions-source`.

## Actualizar código fuente

```bash
cd ../extensions-source
git pull
./../tachimanga-repo/rebuild.sh
```

## Notas

- Los `.jar` que genera el build nuevo de Keiyoushi no los usa Tachimanga
  (formato del nuevo index de Mihon); el script los excluye.
- La firma es `signingkey.jks` propia — mientras uses este repo las updates
  serán consistentes.
