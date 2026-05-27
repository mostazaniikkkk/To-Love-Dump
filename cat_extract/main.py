#!/usr/bin/env python3
"""
Extractor de archivos .CAT — To Love Ru Darkness Birth (PS Vita)

Uso:
    # archivo (--font file es el default)
    cat_extract --from bg/floor_01.cat --save-on out/

    # carpeta
    cat_extract --font folder --from bg/ --save-on out/

    # carpeta + subcarpetas
    cat_extract --font folder --from bg/ --save-on out/ --read-subfolders
"""

import argparse
import os
import traceback

from .parser import parse_cat
from .extractor import extract, dump_info


def _collect_files(source: str, read_subfolders: bool) -> list[str]:
    if read_subfolders:
        files = []
        for root, _dirs, names in os.walk(source):
            for name in names:
                if name.lower().endswith(".cat"):
                    files.append(os.path.join(root, name))
        return sorted(files)

    return sorted(
        os.path.join(source, name)
        for name in os.listdir(source)
        if name.lower().endswith(".cat")
    )


def _process(path: str, save_on: str, source_base: str, info_only: bool, verbose: bool) -> None:
    print(f"\n[{os.path.basename(path)}]")
    try:
        cat = parse_cat(path)
        if info_only:
            dump_info(cat)
        else:
            rel = os.path.relpath(path, source_base)
            out_dir = os.path.join(save_on, os.path.splitext(rel)[0])
            extract(cat, out_dir, verbose=verbose)
            print(f"  -> {out_dir}/")
    except Exception as e:
        print(f"  ERROR: {e}")
        if verbose:
            traceback.print_exc()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extractor de archivos .CAT (To Love Ru Darkness Birth)")

    ap.add_argument("--font", choices=["file", "folder"], default="file",
                    help="Tipo de fuente: 'file' (default) o 'folder'")
    ap.add_argument("--from", dest="source", required=True,
                    help="Ruta del archivo .cat o carpeta de origen")
    ap.add_argument("--save-on", dest="save_on", default=None,
                    help="Carpeta de salida (default: <from>/ripped/)")
    ap.add_argument("--read-subfolders", dest="read_subfolders", action="store_true",
                    help="Analizar subcarpetas (solo con --font folder)")
    ap.add_argument("-i", "--info", action="store_true",
                    help="Solo mostrar información, sin extraer archivos")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Output detallado")

    args = ap.parse_args()

    # --- validaciones ---------------------------------------------------------
    if args.read_subfolders and args.font != "folder":
        ap.error("--read-subfolders solo se puede usar con --font folder")

    if args.font == "folder" and not os.path.isdir(args.source):
        ap.error(f"'{args.source}' no es una carpeta")

    if args.font == "file" and not os.path.isfile(args.source):
        ap.error(f"'{args.source}' no es un archivo")

    # --- directorio de salida -------------------------------------------------
    if args.save_on is None:
        base = args.source if args.font == "folder" else os.path.dirname(args.source)
        args.save_on = os.path.join(base, "ripped")

    # --- recolectar archivos --------------------------------------------------
    if args.font == "folder":
        files = _collect_files(args.source, args.read_subfolders)
        if not files:
            ap.error(f"no se encontraron archivos .cat en '{args.source}'")
        source_base = args.source
    else:
        files = [args.source]
        source_base = os.path.dirname(args.source)

    # --- procesar -------------------------------------------------------------
    for path in files:
        _process(path, args.save_on, source_base, args.info, args.verbose)


if __name__ == "__main__":
    main()
