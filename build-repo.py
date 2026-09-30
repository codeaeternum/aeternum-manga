#!/usr/bin/env python3
"""Genera el repo de Tachimanga:

- index.min.json  (formato legado; los APK se sirven desde apk/)
- index.pb        (formato protobuf nuevo; incluye jarUrl -> jar/, es lo que
                   descarga Tachimanga en iOS/J9)
- apk/, jar/, icon/  copiados desde los build outputs

Uso:  python3 build-repo.py
Requiere haber compilado antes con:
  ./gradlew :src:es:xxx:assembleRelease   (genera apk + jar firmados)
"""

import gzip
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parent / "extensions-source" / "src"
# Los modulos compilados redirigen buildDir aqui (rutas sin espacios para ProGuard)
EXT_BUILD = Path.home() / ".aeternum-ext-build"
INFO_GLOB = "keiyoushi-source-info.json"
ICON_REL = "res/mipmap-xhdpi/ic_launcher.png"

REPO_RAW = "https://raw.githubusercontent.com/codeaeternum/aeternum-manga/main"
SIGNING_KEY = "f06b526e06bb463e48a674d3e51a03e451310038b78b774bb00f499fad97c7f2"

# contentWarning: UNSPECIFIED=0, SAFE=1, MIXED=2, NSFW=3
NSFW_WARNINGS = {2, 3}

# Extensiones muertas: TMO desmantelado por la Policia Nacional (abr-2026).
SKIP_MODULES = {
    "es.tmohentaiunoriginal",
    "es.zonatmoto",
    "es.zonatmoorgunoriginal",
}


# ---------- protobuf encoder (index.proto de keiyoushi/mihon) ----------
def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _str(field: int, value: str) -> bytes:
    if not value:
        return b""
    data = value.encode("utf-8")
    return _tag(field, 2) + _varint(len(data)) + data


def _msg(field: int, data: bytes) -> bytes:
    return _tag(field, 2) + _varint(len(data)) + data


def _int64(field: int, value: int) -> bytes:
    return _tag(field, 0) + _varint(value)


def _source(s: dict) -> bytes:
    out = _int64(1, int(s["id"]))
    out += _str(2, s["name"])
    out += _str(3, s["lang"])
    out += _str(4, s["baseUrl"])
    return out


def _extension(info: dict, apk_name: str, jar_name: str, has_icon: bool) -> bytes:
    res = _str(1, f"{REPO_RAW}/apk/{apk_name}")
    if has_icon:
        res += _str(2, f"{REPO_RAW}/icon/{info['packageName']}.png")
    res += _str(501, f"{REPO_RAW}/jar/{jar_name}")

    out = _str(1, info["name"])
    out += _str(2, info["packageName"])
    out += _msg(3, res)
    out += _str(4, info["extensionLib"])
    out += _int64(5, info["versionCode"])
    out += _str(6, info["versionName"])
    out += _int64(7, info["contentWarning"])
    for s in info["sources"]:
        out += _msg(8, _source(s))
    return out


def _index(extensions: list[bytes]) -> bytes:
    contact = _str(1, "https://github.com/codeaeternum/aeternum-manga")

    ext_list = b"".join(_msg(1, ext) for ext in extensions)

    out = _str(1, "Aeternum")
    out += _str(2, "AET")
    out += _str(3, SIGNING_KEY)
    out += _msg(4, contact)
    out += _msg(101, ext_list)
    return out


# ---------- recoleccion de artefactos ----------
def find_build_dir(module: str) -> Path:
    """buildDir redirigido: ~/.aeternum-ext-build/_src_<lang>_<name>"""
    flat = "_src_" + module.replace(".", "_")
    p = EXT_BUILD / flat
    return p if p.exists() else SRC_ROOT / module.replace(".", "/")


entries = []      # index.min.json (legado)
built = []        # (info, apk_name, jar_name, has_icon) para index.pb

info_files = {}
for info_file in sorted(EXT_BUILD.glob(f"_*/{INFO_GLOB}")) + sorted(
    SRC_ROOT.glob(f"*/*/build/{INFO_GLOB}")
):
    mod = json.loads(info_file.read_text(encoding="utf-8"))["module"]
    info_files.setdefault(mod, info_file)

for info_file in info_files.values():
    info = json.loads(info_file.read_text(encoding="utf-8"))
    if info["module"] in SKIP_MODULES:
        continue

    build_dir = find_build_dir(info["module"])

    apks = list(build_dir.glob("outputs/apk/release/*.apk"))
    jars = list(build_dir.glob("outputs/jar/release/*.jar"))
    if not apks or not jars:
        print(
            f"!! {info['packageName']}: falta apk o jar en {build_dir}, omitido",
            file=sys.stderr,
        )
        continue
    apk, jar = apks[0], jars[0]

    ext_dir = SRC_ROOT / info["module"].replace(".", "/")

    langs = {s["lang"] for s in info["sources"]}
    ext_lang = langs.pop() if len(langs) == 1 else "all"

    entries.append(
        {
            "name": info["name"],
            "pkg": info["packageName"],
            "apk": apk.name,
            "lang": ext_lang,
            "code": info["versionCode"],
            "version": info["versionName"],
            "nsfw": 1 if info["contentWarning"] in NSFW_WARNINGS else 0,
            "sources": [
                {
                    "name": s["name"],
                    "lang": s["lang"],
                    "id": str(s["id"]),
                    "baseUrl": s["baseUrl"],
                }
                for s in info["sources"]
            ],
        }
    )

    for sub, src_file in (("apk", apk), ("jar", jar)):
        d = HERE / sub
        d.mkdir(exist_ok=True)
        shutil.copy2(src_file, d / src_file.name)

    icon = ext_dir / ICON_REL
    has_icon = icon.exists()
    if has_icon:
        icon_dir = HERE / "icon"
        icon_dir.mkdir(exist_ok=True)
        shutil.copy2(icon, icon_dir / f"{info['packageName']}.png")

    built.append((info, apk.name, jar.name, has_icon))
    print(f"ok {info['name']} v{info['versionName']} ({apk.name} + {jar.name})")


entries.sort(key=lambda e: e["pkg"])
built.sort(key=lambda b: b[0]["packageName"])

(HERE / "index.min.json").write_text(
    json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)

pb_extensions = [_extension(info, apk, jar, icon) for info, apk, jar, icon in built]
pb = _index(pb_extensions)
(HERE / "index.pb").write_bytes(gzip.compress(pb, mtime=0))

# index.json: representacion JSON del proto (debugging; Tachimanga lee index.pb)
index_json = {
    "name": "Aeternum",
    "badge_label": "AET",
    "signing_key": SIGNING_KEY,
    "contact": {"website": "https://github.com/codeaeternum/aeternum-manga"},
    "extension_list": {
        "extensions": [
            {
                "name": info["name"],
                "package_name": info["packageName"],
                "resources": {
                    "apk_url": f"{REPO_RAW}/apk/{apk}",
                    **(
                        {"icon_url": f"{REPO_RAW}/icon/{info['packageName']}.png"}
                        if icon
                        else {}
                    ),
                    "jar_url": f"{REPO_RAW}/jar/{jar}",
                },
                "extension_lib": info["extensionLib"],
                "version_code": str(info["versionCode"]),
                "version_name": info["versionName"],
                "content_warning": info["contentWarning"],
                "sources": [
                    {
                        "id": str(s["id"]),
                        "name": s["name"],
                        "language": s["lang"],
                        "home_url": s["baseUrl"],
                    }
                    for s in info["sources"]
                ],
            }
            for info, apk, jar, icon in built
        ]
    },
}
(HERE / "index.json").write_text(
    json.dumps(index_json, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(f"\nindex.min.json: {len(entries)} extensiones")
print(f"index.pb:       {len(pb_extensions)} extensiones ({len(pb)} bytes proto)")
