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
INCLUDE_SUFFIXES = {
    ".kt", ".kts", ".xml", ".png", ".webp", ".proto",
    ".pro", ".json", ".properties", ".jar", ".jks", ".ttf", ".otf",
}


def module_hash(module_dir: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(module_dir.rglob("*")):
        # Dotdirs (.gradle/, .idea/) son cache de build local: existen en
        # disco pero no en el checkout limpio de CI -> hash inestable.
        rel = f.relative_to(module_dir)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if f.is_file() and f.suffix in INCLUDE_SUFFIXES:
            h.update(rel.as_posix().encode())
            data = f.read_bytes()
            # Un checkout con autocrlf (Windows) re-escribe los archivos de
            # texto: normalizar EOL para que el hash sea portable.
            if f.suffix in {".kt", ".kts", ".xml", ".pro", ".json", ".properties", ".proto"}:
                data = data.replace(b"\r\n", b"\n")
            # El versionCode lo escribe el propio bump — normalizarlo fuera
            # del hash o cada bump invalida su propio registro (bucle infinito)
            if f.name == "build.gradle.kts":
                data = VC_RE.sub("versionCode = 0", data.decode("utf-8")).encode("utf-8")
            h.update(data)
    return h.hexdigest()


def main() -> int:
    # Un versions.json truncado (pull interrumpido, conflicto) no debe
    # matar el pipeline entero: resembrar es seguro (provoca un bump de
    # cortesia, no una corrupcion).
    try:
        versions = (
            json.loads(VERSIONS_FILE.read_text())
            if VERSIONS_FILE.exists()
            else {}
        )
        if not isinstance(versions, dict):
            raise ValueError("no es un objeto")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"!! versions.json invalido ({e}) — resembrando", flush=True)
        versions = {}
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

        if record and record.get("hash") == digest:
            continue  # sin cambios

        # Codigo cambio (o modulo nuevo ya publicado): subir versionCode
        base = record.get("versionCode", current) if record else current
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
