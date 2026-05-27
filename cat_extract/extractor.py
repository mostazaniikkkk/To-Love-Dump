import os

from .structs import CatFile


def extract(cat: CatFile, out_dir: str, verbose: bool = False) -> None:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(cat.path))[0]

    # GXT blocks (single o multi)
    for i, block in enumerate(cat.gxt_blocks):
        suffix = f"_{i:02d}" if len(cat.gxt_blocks) > 1 else ""
        block_size = block.header.header_size + block.header.data_size

        # Archivo .gxt completo
        gxt_path = os.path.join(out_dir, f"{base}{suffix}.gxt")
        with open(cat.path, "rb") as src, open(gxt_path, "wb") as dst:
            # Reconstruir bloque: header (0x20) + descriptores + datos
            src.seek(cat.sect0_start)
            if len(cat.gxt_blocks) == 1:
                dst.write(src.read(block_size))
            else:
                # Para multi-GXT calcular offset absoluto del sub-bloque
                offset = cat.sect0_start
                for j, b in enumerate(cat.gxt_blocks):
                    if j == i:
                        src.seek(offset)
                        dst.write(src.read(b.header.header_size + b.header.data_size))
                        break
                    offset += b.header.header_size + b.header.data_size

        if verbose:
            print(f"  GXT{suffix} -> {os.path.basename(gxt_path)}  "
                  f"({block_size} bytes, {block.header.num_textures} tex)")

        # Texturas individuales
        for j, tex in enumerate(block.textures):
            raw = block.data[tex.data_offset: tex.data_offset + tex.data_size]
            p = os.path.join(out_dir, f"{base}{suffix}_tex{j:02d}_{tex.width}x{tex.height}.bin")
            with open(p, "wb") as f:
                f.write(raw)
            if verbose:
                print(f"  TEX{suffix}[{j}] -> {os.path.basename(p)}  "
                      f"fmt=0x{tex.tex_format:08X}  {tex.width}x{tex.height}")

    # TMD0
    if cat.tmd0_raw is not None:
        p = os.path.join(out_dir, f"{base}.tmd0")
        with open(p, "wb") as f:
            f.write(cat.tmd0_raw)
        if verbose:
            print(f"  TMD0 -> {os.path.basename(p)}  ({len(cat.tmd0_raw)} bytes)")

    # TMO0
    if cat.tmo0_raw is not None:
        p = os.path.join(out_dir, f"{base}.tmo0")
        with open(p, "wb") as f:
            f.write(cat.tmo0_raw)
        if verbose:
            print(f"  TMO0 -> {os.path.basename(p)}  ({len(cat.tmo0_raw)} bytes)")

    # Scenes
    for i, scene in enumerate(cat.scenes):
        suffix = f"_scene{i}" if len(cat.scenes) > 1 else "_scene"
        p = os.path.join(out_dir, f"{base}{suffix}.scn")
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"scene_name : {scene.scene_name}\n")
            f.write(f"version    : {scene.version}\n")
            f.write(f"objects    : {len(scene.objects)}\n\n")
            for obj in scene.objects:
                f.write(f"  [{obj.obj_type}] {obj.name}\n")
                f.write(f"    pos   : {obj.position}\n")
                f.write(f"    scale : {obj.scale}\n")
                f.write(f"    rot   : {obj.rotation}\n")
        if verbose:
            print(f"  SCN{i}  -> {os.path.basename(p)}  ({len(scene.objects)} objetos)")

    # Name table
    if cat.name_table:
        p = os.path.join(out_dir, f"{base}_nametable.txt")
        with open(p, "w", encoding="utf-8") as f:
            for i, name in enumerate(cat.name_table):
                f.write(f"{i:2d}  {name}\n")
        if verbose:
            print(f"  NAM  -> {os.path.basename(p)}  "
                  f"({len(cat.name_table)} entradas: {', '.join(cat.name_table)})")

    # Shader/nested entries (num_sections=1)
    if cat.shader_entries:
        for e in cat.shader_entries:
            if e.nested_cat is not None:
                nested_dir = os.path.join(out_dir, f"entry_{e.index:02d}")
                extract(e.nested_cat, nested_dir, verbose=verbose)
                if verbose:
                    print(f"  CAT[{e.index}] -> {os.path.relpath(nested_dir, out_dir)}/  "
                          f"({e.size} bytes)")
            else:
                p = os.path.join(out_dir, f"entry_{e.index:02d}.bin")
                with open(p, "wb") as f:
                    f.write(e.data)
                if verbose:
                    print(f"  RAW[{e.index}] -> {os.path.basename(p)}  ({e.size} bytes)")

    # Script entries (version=3)
    if cat.script_entries:
        p = os.path.join(out_dir, f"{base}_index.txt")
        with open(p, "w", encoding="utf-8") as f:
            for e in cat.script_entries:
                typ = "TAMS" if e.magic == 0x534D4154 else "filename"
                f.write(f"{e.index:3d}  {e.filename:<20s}  {typ}  size=0x{e.size:X}\n")
        if verbose:
            print(f"  IDX  -> {os.path.basename(p)}  ({len(cat.script_entries)} entradas)")
        for e in cat.script_entries:
            if e.magic == 0x534D4154 and e.body:
                fname = e.filename if e.filename else f"entry_{e.index:03d}.bin"
                p = os.path.join(out_dir, fname)
                with open(p, "wb") as f:
                    f.write(e.body)
                if verbose:
                    print(f"  TAMS[{e.index}] -> {fname}  (0x{e.size:X} bytes)")


def dump_info(cat: CatFile) -> None:
    h = cat.header
    si = cat.section_info
    print(f"  version      : {h.version}")
    print(f"  num_sections : {h.num_sections}")
    print(f"  toc_offset   : 0x{h.toc_offset:X}")
    print(f"  sect0_start  : 0x{cat.sect0_start:X}")

    if si is not None:
        if h.num_sections == 3:
            print(f"  sect1_start  : 0x{si.sect1_start:X}")
            print(f"  sect2_start  : 0x{si.sect2_start:X}")
            print(f"  gxt_blocks   : {len(cat.gxt_blocks)}")
        elif h.num_sections == 4:
            print(f"  sect1_start  : 0x{si.sect1_start:X}")
            print(f"  sect2_start  : 0x{si.sect2_start:X}")
            print(f"  sect3_start  : 0x{si.sect3_start:X}")
        elif h.num_sections == 5:
            print(f"  sect1_start  : 0x{si.sect1_start:X}")
            print(f"  sect2_start  : 0x{si.sect2_start:X}")
            print(f"  sect3_start  : 0x{si.sect3_start:X}")
            print(f"  sect4_start  : 0x{si.sect4_start:X}")
        elif h.num_sections == 6:
            print(f"  sect1_start  : 0x{si.sect1_start:X}")
            print(f"  sect2_start  : 0x{si.sect2_start:X}")
            print(f"  sect3_start  : 0x{si.sect3_start:X}")
            print(f"  sect4_start  : 0x{si.sect4_start:X}")
            print(f"  sect5_start  : 0x{si.sect5_start:X}")
        elif h.num_sections == 2:
            print(f"  sect1_start  : 0x{si.sect1_start:X}")

    for i, block in enumerate(cat.gxt_blocks):
        g = block.header
        print(f"  GXT[{i}] version=0x{g.version:X}  textures={g.num_textures}")
        for j, t in enumerate(block.textures):
            print(f"    tex[{j}] {t.width}x{t.height}  fmt=0x{t.tex_format:08X}  "
                  f"size=0x{t.data_size:X}")

    if cat.tmd0_raw:
        print(f"  TMD0         : {len(cat.tmd0_raw)} bytes")
    if cat.tmo0_raw:
        print(f"  TMO0         : {len(cat.tmo0_raw)} bytes")

    for i, scene in enumerate(cat.scenes):
        print(f"  scene[{i}] name: {scene.scene_name}  objects={len(scene.objects)}")
        for obj in scene.objects:
            print(f"    [{obj.obj_type:12s}] {obj.name}")

    if cat.name_table:
        print(f"  name_table   : {cat.name_table}")

    if cat.shader_entries:
        cats   = sum(1 for e in cat.shader_entries if e.nested_cat is not None)
        raws   = len(cat.shader_entries) - cats
        print(f"  n=1 entries  : {len(cat.shader_entries)}  ({cats} CAT anidados, {raws} raw)")
        for e in cat.shader_entries:
            label = f"CAT[{e.index}]" if e.nested_cat else f"raw[{e.index}]"
            print(f"    {label}  offset=0x{e.offset:X}  size=0x{e.size:X}")

    if cat.script_entries:
        print(f"  script (v3)  : {len(cat.script_entries)} entradas")
        for e in cat.script_entries:
            typ = "TAMS" if e.magic == 0x534D4154 else "filename"
            print(f"    [{e.index:3d}] {e.filename:<20s}  {typ}  size=0x{e.size:X}")
