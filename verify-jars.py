#!/usr/bin/env python3
"""Verificador post-build de los jars de extension (Tachimanga iOS / OpenJ9).

Detecta ANTES de publicar los problemas que matan una extension en iOS:

1. Firma:      META-INF/*.SF + *.RSA presentes en el zip.
2. Clases:     al menos una clase bajo eu/kanade/tachiyomi/ (ProGuard aplana
               eu.kanade.tachiyomi.extension.* -> eu.kanade.tachiyomi.a.a.a.*,
               asi que se comprueba el prefijo, no el path literal).
3. jdeps:      referencias a clases android.*/androidx.* cotejadas con la lista
               de stubs que Tachimanga provee. Cualquier clase android fuera de
               la lista = VerifyError/NoClassDefFoundError seguro en iOS.

La lista ANDROID_STUBS se calibro empiricamente (jdeps sobre los 9 jars
publicados): son las unicas clases android que usan TODOS los modulos sin
ConfigurableSource, o sea lo que Tachimanga stub-ea de serie.

Las clases de PREFS_ANDROID_REFS solo aparecen en es.rncalation (unico modulo
ConfigurableSource): se toleran solo ahi; con --strict-prefs fallan siempre.
Asi, un modulo nuevo que cuele prefs/WebView/android.graphics rompe CI.

Uso:  python3 verify-jars.py [--strict-prefs] [-v]
Requiere jdeps (JDK): $JAVA_HOME/bin/jdeps o jdeps en PATH.
Exit 0 si todos los jars pasan; 1 si alguno falla o no hay jars.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parent / "extensions-source" / "src"
# Los modulos compilados redirigen buildDir aqui (igual que en build-repo.py)
EXT_BUILD = Path.home() / ".aeternum-ext-build"
INFO_GLOB = "keiyoushi-source-info.json"

# Mismas extensiones muertas que omite build-repo.py
SKIP_MODULES = {
    "es.tmohentaiunoriginal",
    "es.zonatmoto",
    "es.zonatmoorgunoriginal",
}

# Stubs android confirmados en Tachimanga iOS: presentes en los 8 modulos
# sin ConfigurableSource (jdeps -verbose:class, jars publicados v1.6.x).
ANDROID_STUBS = {
    "android.app.Activity",
    "android.app.Application",
    "android.content.ActivityNotFoundException",
    "android.content.Intent",
    "android.net.Uri",
    "android.os.Bundle",
    "android.os.LocaleList",
    "android.os.SystemClock",
    "android.util.Log",
}

# Solo aparecen en es.rncalation (ConfigurableSource). Tachimanga los tolera
# HOY porque rncalation ya se publica asi, pero son la clase de refs que
# rompe iOS si cuelan en un modulo nuevo.
PREFS_ANDROID_REFS = {
    "android.content.Context",
    "android.content.SharedPreferences",
    "androidx.preference.EditTextPreference",
    "androidx.preference.Preference",
    "androidx.preference.PreferenceScreen",
}

# Modulos con ConfigurableSource conocidos: se les toleran las prefs refs
# en modo normal; --strict-prefs se las cuenta como fallo a ellos tambien.
PREFS_MODULES = {"es.rncalation"}

# java.* considerado trivialmente presente en cualquier JVM (incl. OpenJ9).
# Cualquier otra clase java.* referenciada se reporta como exotica (info).
JAVA_COMMON_PREFIXES = (
    "java.lang",
    "java.util",
    "java.io",
    "java.nio",
    "java.net",
    "java.time",
)

# Linea de dependencia de `jdeps -verbose:class`:
#   <clase-origen>   -> <clase-destino>   <java.base|not found|<jar>>
DEP_RE = re.compile(r"^\s+\S+\s+->\s+(\S+)\s+(\S.*?)\s*$")


def find_jdeps() -> str | None:
    """$JAVA_HOME/bin/jdeps, si no jdeps en PATH. None si ninguno funciona."""
    candidates = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin" / "jdeps")
    path_jdeps = shutil.which("jdeps")
    if path_jdeps:
        candidates.append(Path(path_jdeps))
    for c in candidates:
        if c.exists():
            try:
                # Preflight: en macOS /usr/bin/jdeps es un stub sin JDK
                subprocess.run(
                    [str(c), "--version"],
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
                return str(c)
            except (subprocess.SubprocessError, OSError):
                continue
    return None


def find_build_dir(module: str) -> Path:
    """Igual que build-repo.py: buildDir redirigido o src/.../build."""
    flat = "_src_" + module.replace(".", "_")
    p = EXT_BUILD / flat
    return p if p.exists() else SRC_ROOT / module.replace(".", "/") / "build"


def expected_modules() -> set[str]:
    """Los modulos canonicos: patches/modules/<lang>/<name> -> <lang>.<name>.

    El verificador no debe pasar en silencio si un modulo no produce jar
    (info-json ausente o glob fallado): la lista esperada viene del disco,
    no solo de lo que el build decidio emitir.
    """
    return {
        f"{lang.name}.{mod.name}"
        for lang in (HERE / "patches" / "modules").iterdir()
        if lang.is_dir()
        for mod in lang.iterdir()
        if mod.is_dir()
    }


def discover_jars() -> tuple[list[dict], set[str]]:
    """Un jar por modulo, emparejado por versionName (como build-repo.py).

    El dir de salida acumula builds viejos; el keiyoushi-source-info.json
    marca cual es el que se publicaria. Devuelve (jars encontrados,
    modulos esperados sin jar) — el caller falla si falta alguno.
    """
    expected = expected_modules()
    info_files = {}
    for info_file in sorted(EXT_BUILD.glob(f"_*/{INFO_GLOB}")) + sorted(
        SRC_ROOT.glob(f"*/*/build/{INFO_GLOB}")
    ):
        mod = json.loads(info_file.read_text(encoding="utf-8"))["module"]
        info_files.setdefault(mod, info_file)

    found, missing = [], set(expected)
    for info_file in info_files.values():
        info = json.loads(info_file.read_text(encoding="utf-8"))
        module = info["module"]
        if module in SKIP_MODULES:
            continue
        if module not in expected:
            # Artefacto residual de un modulo ya retirado: no se publica.
            print(f"-- {module}: sin patches/modules correspondiente, ignorado")
            continue
        ver = info["versionName"]
        jars = sorted(
            find_build_dir(module).glob(f"outputs/jar/release/*-v{ver}.jar")
        )
        if not jars:
            print(
                f"!! {module}: falta jar v{ver} en {find_build_dir(module)}",
                file=sys.stderr,
            )
            continue
        missing.discard(module)
        found.append({"module": module, "version": ver, "jar": jars[0]})
    return found, missing


def check_signature(jar: Path) -> list[str]:
    """Devuelve problemas de firma ([] = firmado)."""
    problems = []
    try:
        names = zipfile.ZipFile(jar).namelist()
    except zipfile.BadZipFile:
        return ["no es un zip valido"]
    meta = {n for n in names if n.startswith("META-INF/")}
    if not any(n.upper().endswith(".SF") for n in meta):
        problems.append("falta META-INF/*.SF")
    if not any(
        n.upper().endswith((".RSA", ".DSA", ".EC")) for n in meta
    ):
        problems.append("falta META-INF/*.RSA")
    return problems


def jar_class_names(jar: Path) -> set[str]:
    try:
        return {n for n in zipfile.ZipFile(jar).namelist() if n.endswith(".class")}
    except zipfile.BadZipFile:
        return set()


def jdeps_refs(jdeps: str, jar: Path) -> tuple[set[str], set[str], str | None]:
    """Ejecuta jdeps -verbose:class.

    Devuelve (todas las clases referenciadas, las 'not found', error|None).
    """
    try:
        proc = subprocess.run(
            [jdeps, "-verbose:class", str(jar)],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.SubprocessError, OSError) as e:
        return set(), set(), f"jdeps no ejecutable: {e}"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip().splitlines()
        return set(), set(), f"jdeps exit {proc.returncode}: {err[0] if err else ''}"

    refs, not_found = set(), set()
    for line in proc.stdout.splitlines():
        m = DEP_RE.match(line)
        if not m:
            continue
        target, where = m.group(1), m.group(2)
        if "." not in target:
            continue  # paquete suelto, no FQCN
        refs.add(target)
        if where == "not found":
            not_found.add(target)
    return refs, not_found, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict-prefs",
        action="store_true",
        help="cuenta las refs prefs-dependent como fallo incluso en "
        "los modulos ConfigurableSource conocidos",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    jdeps = find_jdeps()
    if not jdeps:
        print(
            "!! no se encontro jdeps funcional "
            "(probado $JAVA_HOME/bin/jdeps y PATH)",
            file=sys.stderr,
        )
        return 1

    jars, missing = discover_jars()
    if not jars and not missing:
        print("!! no se encontro ningun jar para verificar", file=sys.stderr)
        return 1

    failures = 0
    for module in sorted(missing):
        failures += 1
        print(f"FAIL {module} (sin jar construido)")
    if missing:
        print()
    print(f"jdeps: {jdeps}")
    print(f"strict-prefs: {'ON' if args.strict_prefs else 'off'}\n")

    for item in sorted(jars, key=lambda i: i["module"]):
        module, jar = item["module"], item["jar"]
        problems, notes = [], []

        sig_problems = check_signature(jar)
        problems += [f"firma: {p}" for p in sig_problems]

        classes = jar_class_names(jar)
        if not any(n.startswith("eu/kanade/tachiyomi/") for n in classes):
            problems.append("sin clases eu/kanade/tachiyomi/**")

        refs, not_found, err = jdeps_refs(jdeps, jar)
        if err:
            problems.append(err)
        else:
            android_refs = {
                r for r in refs if r.startswith(("android.", "androidx."))
            }
            exotic_java = sorted(
                r
                for r in refs
                if r.startswith("java.")
                and not r.startswith(JAVA_COMMON_PREFIXES)
            )
            unknown = sorted(
                android_refs - ANDROID_STUBS - PREFS_ANDROID_REFS
            )
            prefs_hits = sorted(android_refs & PREFS_ANDROID_REFS)

            if unknown:
                problems.append(
                    "refs android fuera de stubs Tachimanga: "
                    + ", ".join(unknown)
                )
            if prefs_hits:
                allowed = module in PREFS_MODULES and not args.strict_prefs
                msg = "refs prefs-dependent: " + ", ".join(prefs_hits)
                if allowed:
                    notes.append("RISKY (ConfigurableSource conocido) " + msg)
                else:
                    problems.append(msg)
            if exotic_java:
                notes.append("java.* exotico: " + ", ".join(exotic_java))
            if args.verbose:
                notes.append(
                    f"{len(refs)} refs totales, {len(not_found)} 'not found'"
                )
                notes.append(
                    "android refs: "
                    + (", ".join(sorted(android_refs)) or "ninguna")
                )

        if problems:
            failures += 1
            print(f"FAIL {module} ({jar.name})")
            for p in problems:
                print(f"     !! {p}")
        else:
            print(f"PASS {module} ({jar.name})")
        for n in notes:
            print(f"     -- {n}")

    print(f"\n{len(jars) - failures}/{len(jars)} jars OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
