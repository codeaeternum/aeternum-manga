#!/usr/bin/env python3
"""Genera index.min.json (formato legado que lee Tachimanga) + copia APKs e iconos
desde los build outputs de extensions-source.

Uso:  python3 build-repo.py
Requiere haber compilado antes con:
  ./gradlew :src:es:xxx:assembleRelease -x :src:es:xxx:createReleaseExtensionJar -x :src:es:xxx:signReleaseExtensionJar
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parent / "extensions-source" / "src"
APK_GLOB = "build/outputs/apk/release/*.apk"
INFO_GLOB = "build/keiyoushi-source-info.json"
ICON_REL = "res/mipmap-xhdpi/ic_launcher.png"

# contentWarning ordinal+1: UNSPECIFIED=0, SAFE=1, MIXED=2, NSFW=3
NSFW_WARNINGS = {2, 3}

entries = []
for info_file in sorted(SRC_ROOT.glob(f"*/*/{INFO_GLOB}")):
    info = json.loads(info_file.read_text(encoding="utf-8"))
    ext_dir = info_file.parents[1]

    apks = list(ext_dir.glob(APK_GLOB))
    if not apks:
        print(f"!! {info['packageName']}: sin APK compilado, omitido", file=sys.stderr)
        continue
    apk = apks[0]

    langs = {s["lang"] for s in info["sources"]}
    ext_lang = langs.pop() if len(langs) == 1 else "all"

    entry = {
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
                "versionId": 1,
            }
            for s in info["sources"]
        ],
    }
    entries.append(entry)

    shutil.copy2(apk, HERE / apk.name)

    icon = ext_dir / ICON_REL
    if icon.exists():
        icon_dir = HERE / "icon"
        icon_dir.mkdir(exist_ok=True)
        shutil.copy2(icon, icon_dir / f"{info['packageName']}.png")

    print(f"ok {info['name']} v{info['versionName']} ({apk.name})")

index = HERE / "index.min.json"
index.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"\nindex.min.json: {len(entries)} extensiones")
