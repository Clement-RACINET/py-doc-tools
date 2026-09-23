#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Script pour annoter uniquement les fichiers non couverts par reuse.toml."""

from __future__ import annotations

import fnmatch
import subprocess
import sys
import tomllib
from pathlib import Path

try:
    from reuse.project import Project
except ImportError:
    err_msg = (
        "Erreur : La bibliothèque 'reuse' n'est pas installée dans l'environnement courant.\n"
        "Installez-la via 'pip install reuse' ou activez votre environnement virtuel."
    )
    print(err_msg, file=sys.stderr)
    sys.exit(1)


COPYRIGHT_HOLDER = "C. RACINET"
LICENSE_ID = "X11"
YEAR = "2026"


def get_toml_ignored_patterns(toml_path: Path) -> list[str]:
    """Charge l'ensemble des chemins et globs définis dans reuse.toml."""
    if not toml_path.is_file():
        return []

    try:
        with toml_path.open("rb") as fp:
            data = tomllib.load(fp)
    except Exception as exc:  # noqa: BLE001
        print(
            f"[-] Avertissement : impossible de lire {toml_path}: {exc}",
            file=sys.stderr,
        )
        return []

    patterns: list[str] = []
    annotations = data.get("annotations", [])
    if isinstance(annotations, list):
        for entry in annotations:
            if not isinstance(entry, dict):
                continue
            path_val = entry.get("path")
            if isinstance(path_val, str):
                patterns.append(path_val)
            elif isinstance(path_val, list):
                for p in path_val:
                    if isinstance(p, str):
                        patterns.append(p)

    return patterns


def is_path_matching_patterns(rel_posix_path: str, patterns: list[str]) -> bool:
    """Vérifie si un chemin relatif correspond à l'un des globs du reuse.toml."""
    for pattern in patterns:
        norm_pattern = pattern.rstrip("/")
        # Correspondance exacte ou via glob
        if fnmatch.fnmatch(rel_posix_path, norm_pattern):
            return True
        # Gestion des motifs récursifs de type "dir/**"
        if norm_pattern.endswith("/**"):
            prefix = norm_pattern[:-3]
            if rel_posix_path == prefix or rel_posix_path.startswith(f"{prefix}/"):
                return True
        # Gestion des préfixes de dossier direct
        if rel_posix_path.startswith(f"{norm_pattern}/"):
            return True
    return False


def find_files_to_annotate(root_dir: Path) -> list[str]:
    """Parcourt le projet et retourne uniquement les fichiers nécessitant un en-tête."""
    project = Project.from_directory(root_dir)
    toml_patterns = get_toml_ignored_patterns(root_dir / "reuse.toml")
    files_to_annotate: list[str] = []

    for file_path in project.all_files():
        rel_posix = project.relative_from_root(file_path).as_posix()

        # 1. Ignorer les fichiers couverts par reuse.toml
        if is_path_matching_patterns(rel_posix, toml_patterns):
            continue

        # 2. Ignorer les fichiers qui possèdent déjà un en-tête ou un fichier .license
        # L'API REUSE moderne expose reuse_info_of(path)
        info_getter = getattr(project, "reuse_info_of", None) or getattr(
            project, "spdx_info_of", None
        )
        if callable(info_getter):
            info = info_getter(file_path)
            if info is not None:
                spdx_exprs = getattr(info, "spdx_expressions", None)
                if spdx_exprs and len(spdx_exprs) > 0:
                    continue

        files_to_annotate.append(str(file_path))

    return files_to_annotate


def main() -> None:
    """Point d'entrée principal du script."""
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent

    print(f"[*] Analyse du projet depuis : {root_dir}")
    targets = find_files_to_annotate(root_dir)

    if not targets:
        print(
            "[+] Aucun fichier à annoter ! Tous les fichiers sont couverts ou conformes."
        )
        return

    print(f"[*] {len(targets)} fichier(s) à annoter détecté(s) :")
    for f in targets:
        print(f"  - {Path(f).relative_to(root_dir)}")

    cmd = [
        "reuse",
        "annotate",
        "--copyright",
        COPYRIGHT_HOLDER,
        "--license",
        LICENSE_ID,
        "--year",
        YEAR,
        "--skip-unrecognised",
        *targets,
    ]

    print("\n[*] Application des annotations SPDX...")
    res = subprocess.run(cmd, cwd=root_dir, check=False)
    if res.returncode == 0:
        print(
            "\n[+] Opération terminée avec succès. Vous pouvez exécuter 'reuse lint'."
        )
    else:
        print(
            f"\n[-] Erreur lors de l'annotation (code {res.returncode})",
            file=sys.stderr,
        )
        sys.exit(res.returncode)


if __name__ == "__main__":
    main()
