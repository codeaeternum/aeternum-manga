# Aeternum Manga

Repo personal de extensiones para Tachimanga/Mihon (formato legado
`index.min.json`), compilada desde
[`keiyoushi/extensions-source`](https://github.com/keiyoushi/extensions-source)
con firma propia.

## Añadir en Tachimanga

1. En Tachimanga: **More → Extensions → Extension Repositories → Add Repository**
2. Pega la URL del `index.min.json`:

   ```
   https://raw.githubusercontent.com/codeaeternum/aeternum-manga/main/index.min.json
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
| LectorTMOo | es | Propia (lectortmo.online) |
| TuMangaHentai | es | Propia (tumangahentai.com), NSFW |

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
