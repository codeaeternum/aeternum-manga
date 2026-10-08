#!/usr/bin/env python3
"""Auto-bump de versionCode para los modulos propios.

Por cada modulo en patches/modules/<lang>/<name>/:
- Calcula un hash de todo su contenido fuente.
- Si el hash difiere del publicado (versions.json) -> sube versionCode
  en build.gradle.kts para que Tachimanga lo vea como update.
- Si no cambio -> no toca nada.

Corre ANTES de compilar (rebuild.sh / CI lo invocan primero).
"""

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULES_DIR = HERE / "patches" / "modules"
VERSIONS_FILE = HERE / "versions.json"
VC_RE = re.compile(r"versionCode\s*=\s*(\d+)")

# Archivos que no influyen en el bytecode pero forman parte del modulo
# (el icono si afecta al apk -> incluimos res/ en el hash)
INCLUDE_SUFFIXES = {".kt", ".kts", ".xml", ".png", ".webp", ".proto"}


def module_hash(module_dir: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(module_dir.rglob("*")):
        if f.is_file() and f.suffix in INCLUDE_SUFFIXES:
            h.update(f.relative_to(module_dir).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def main() -> int:
    versions = json.loads(VERSIONS_FILE.read_text()) if VERSIONS_FILE.exists() else {}
    bumped = []

    for gradle in sorted(MODULES_DIR.glob("*/*/build.gradle.kts")):
        module_dir = gradle.parent
        mod = module_dir.relative_to(MODULES_DIR).as_posix()  # e.g. es/lectortmoo
        text = gradle.read_text(encoding="utf-8")
        m = VC_RE.search(text)
        if not m:
            print(f"!! {mod}: sin versionCode, omitido")
            continue

        current = int(m.group(1))
        digest = module_hash(module_dir)
        record = versions.get(mod)

        if record and record["hash"] == digest:
            continue  # sin cambios

        # Codigo cambio (o modulo nuevo ya publicado): subir versionCode
        base = record["versionCode"] if record else current
        new_code = max(current, base + 1) if record else current
        if record:
            gradle.write_text(
                text[: m.start(1)] + str(new_code) + text[m.end(1) :], encoding="utf-8"
            )
            bumped.append(f"{mod}: v1.6.{new_code}")
        versions[mod] = {"hash": digest, "versionCode": new_code}

    VERSIONS_FILE.write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")
    print("bumped: " + (", ".join(bumped) if bumped else "ninguno"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
