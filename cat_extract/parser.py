import struct

from .structs import (
    MainHeader,
    SectionInfo1, SectionInfo2, SectionInfo3, SectionInfo4, SectionInfo5, SectionInfo6,
    GxtHeader, GxtTexture, GxtBlock,
    SceneObject, SceneData,
    ScriptEntry, ShaderEntry,
    CatFile,
)
from .utils import u32, read_pstring, read_vec3


GXT_MAGIC  = 0x00545847  # "GXT\0" LE
TMO0_MAGIC = 0x306F6D74  # "tmo0" LE
TMD0_MAGIC = 0x30646D74  # "tmd0" LE
TAMS_MAGIC = 0x534D4154  # "TAMS" LE


def parse_main_header(data: bytes) -> MainHeader:
    version, num_sections, reserved, toc_offset = struct.unpack_from("<4I", data, 0)
    return MainHeader(version, num_sections, reserved, toc_offset)


def parse_section_info(data: bytes, num_sections: int) -> object:
    if num_sections == 1:
        return SectionInfo1(*struct.unpack_from("<4I", data, 0x10))
    if num_sections == 2:
        return SectionInfo2(*struct.unpack_from("<8I", data, 0x10))
    if num_sections == 3:
        return SectionInfo3(*struct.unpack_from("<12I", data, 0x10))
    if num_sections == 4:
        return SectionInfo4(*struct.unpack_from("<16I", data, 0x10))
    if num_sections == 5:
        return SectionInfo5(*struct.unpack_from("<20I", data, 0x10))
    if num_sections == 6:
        return SectionInfo6(*struct.unpack_from("<24I", data, 0x10))
    hexdump = " ".join(f"{b:02X}" for b in data[0: 0x10 + num_sections * 16])
    raise ValueError(
        f"num_sections no soportado: {num_sections}\n"
        f"  header completo (0x00..0x{0x10 + num_sections * 16:02X}): {hexdump}"
    )


def _sect0_start(data: bytes, toc_offset: int) -> int:
    # Universal: sect0_start = toc_offset + TOC_Row1[1]  (u32 at toc_offset+20)
    return toc_offset + struct.unpack_from("<I", data, toc_offset + 20)[0]


def _parse_gxt_block(data: bytes, offset: int) -> GxtBlock:
    magic, version, num_tex, hdr_size, data_size, np4, np8, pad = \
        struct.unpack_from("<8I", data, offset)

    if magic != GXT_MAGIC:
        hexdump = " ".join(f"{b:02X}" for b in data[offset: offset + 16])
        raise ValueError(
            f"Magic GXT inválido: 0x{magic:08X} en sect0_start=0x{offset:X}\n"
            f"  primeros 16 bytes: {hexdump}\n"
            f"  file_size=0x{len(data):X}"
        )

    hdr = GxtHeader(magic, version, num_tex, hdr_size, data_size, np4, np8, pad)

    textures = []
    desc_offset = offset + 0x20   # GxtHeader ocupa 8×u32 = 0x20 bytes
    for _ in range(num_tex):
        d_off, d_size, pal_idx, flags, typ, base_sz = \
            struct.unpack_from("<6I", data, desc_offset)
        width, height = struct.unpack_from("<2H", data, desc_offset + 0x18)
        tex_fmt = u32(data, desc_offset + 0x1C)
        textures.append(GxtTexture(d_off, d_size, pal_idx, flags, typ, base_sz,
                                   width, height, tex_fmt))
        desc_offset += 0x20

    tex_data = data[offset + hdr_size: offset + hdr_size + data_size]
    return GxtBlock(hdr, textures, tex_data)


def _parse_gxt_single(data: bytes, sect0_start: int) -> list[GxtBlock]:
    return [_parse_gxt_block(data, sect0_start)]


def _parse_gxt_multi(data: bytes, toc_offset: int, gxt_sub_count: int) -> list[GxtBlock]:
    toc_row1 = struct.unpack_from("<4I", data, toc_offset + 16)
    first_gxt_start = toc_offset + toc_row1[1]

    blocks = []
    offset = first_gxt_start
    for _ in range(gxt_sub_count):
        block = _parse_gxt_block(data, offset)
        blocks.append(block)
        offset += block.header.header_size + block.header.data_size
    return blocks


def parse_name_table(data: bytes, offset: int) -> list[str]:
    entry_count = u32(data, offset + 0x20)
    entries = []
    entry_offset = offset + 0x30
    for _ in range(entry_count):
        raw = data[entry_offset: entry_offset + 0x20]
        entries.append(raw.split(b"\x00")[0].decode("ascii", errors="replace"))
        entry_offset += 0x20
    return entries


def _parse_scene_sub_header(data: bytes, offset: int) -> tuple[int, list[int], list[int]]:
    sub_block_count = u32(data, offset + 0x04)
    inner_header_size = u32(data, offset + 0x0C)

    arr_base = offset + 0x10
    offsets = [u32(data, arr_base + i * 4) for i in range(sub_block_count)]
    arr_base2 = arr_base + sub_block_count * 4
    sizes = [u32(data, arr_base2 + i * 4) for i in range(sub_block_count)]

    return inner_header_size, offsets, sizes


def _parse_scene_header_block(data: bytes, offset: int) -> tuple[str, int, int]:
    start = offset
    _ver_str, offset = read_pstring(data, offset)
    version_num = u32(data, offset); offset += 4
    offset += 4  # reserved
    scene_name, offset = read_pstring(data, offset)
    return scene_name, version_num, offset - start


def _try_parse_objects(data: bytes, offset: int, end: int) -> list[SceneObject]:
    objects = []
    pos = offset
    while pos < end:
        try:
            name, pos = read_pstring(data, pos)
            if not name:
                break
            position, pos = read_vec3(data, pos)
            scale, pos    = read_vec3(data, pos)
            rotation, pos = read_vec3(data, pos)
            obj_type, pos = read_pstring(data, pos)
            objects.append(SceneObject(name, position, scale, rotation, obj_type))
        except Exception:
            break
    return objects


def parse_scene_section(data: bytes, sect_offset: int, sect_size: int) -> SceneData:
    inner_hdr_size, rel_offsets, rel_sizes = _parse_scene_sub_header(data, sect_offset)

    first_block_abs = sect_offset + inner_hdr_size + 2 * len(rel_offsets) * 4
    scene_name, version_num, consumed = _parse_scene_header_block(data, first_block_abs)

    obj_start = first_block_abs + consumed
    obj_end   = first_block_abs + (rel_sizes[0] if rel_sizes else sect_size)
    objects = _try_parse_objects(data, obj_start, obj_end)

    sub_blocks_raw = []
    for i, (rel_off, sz) in enumerate(zip(rel_offsets, rel_sizes)):
        if sz == 0:
            continue
        abs_off = first_block_abs + rel_off
        sub_blocks_raw.append((i, rel_off, data[abs_off: abs_off + sz]))

    return SceneData(scene_name, version_num, objects, sub_blocks_raw)


def _try_parse_scene(data: bytes, sect_start: int, sect_size: int) -> SceneData | None:
    try:
        return parse_scene_section(data, sect_start, sect_size)
    except Exception:
        return None


def _parse_story_cat(data: bytes, path: str, hdr: MainHeader) -> CatFile:
    data_start = hdr.toc_offset  # u32 at 0x0C

    entries    = []
    idx_base   = 0x10  # índice empieza tras los 16 bytes de header
    body_start = data_start
    i          = 0

    while True:
        body_size, fname_start, fname_end = struct.unpack_from("<3I", data, idx_base + i * 12)
        if body_size == 0xFFFFFFFF:  # sentinel
            break
        body      = data[body_start: body_start + body_size]
        magic     = u32(data, body_start) if body_size >= 4 else 0
        fname_raw = data[fname_start: fname_start + 0x30]  # filename = 48 bytes
        filename  = fname_raw.rstrip(b'\x00').decode('ascii', errors='replace')
        entries.append(ScriptEntry(i, body_start, body_size, fname_start, magic, body, filename))
        body_start = fname_end  # siguiente body empieza tras este filename
        i += 1

    toc_raw = data[0x10: data_start]
    return CatFile(path, hdr, None, toc_raw, data_start, script_entries=entries)


def _parse_script_cat(data: bytes, path: str, hdr: MainHeader) -> CatFile:
    toc_offset  = 0x20
    entry_count = u32(data, 0x18)
    toc_raw     = data[toc_offset: toc_offset + 0x10]

    base    = toc_offset + 0x10 + 4  # saltar Row[0] (16 bytes) + cero líder (4 bytes)
    offsets = [u32(data, base + i * 4)                   for i in range(entry_count)]
    sizes   = [u32(data, base + entry_count * 4 + i * 4) for i in range(entry_count)]
    ends    = [u32(data, base + entry_count * 8 + i * 4) for i in range(entry_count)]

    entries = []
    for i in range(entry_count):
        entry_pos = toc_offset + offsets[i]
        magic     = u32(data, entry_pos)
        body      = data[entry_pos: entry_pos + sizes[i]]
        if magic == TAMS_MAGIC:
            filename_raw = data[toc_offset + ends[i]: toc_offset + ends[i] + 16]
        else:
            filename_raw = body[:16]
        filename = filename_raw.rstrip(b'\x00').decode('ascii', errors='replace')
        entries.append(ScriptEntry(i, offsets[i], sizes[i], ends[i], magic, body, filename))

    return CatFile(path, hdr, None, toc_raw, toc_offset, script_entries=entries)


def _parse_n1_cat(data: bytes, path: str, hdr: MainHeader, si: SectionInfo1,
                  toc_offset: int) -> CatFile:
    entry_count  = si.entry_count
    offsets_base = toc_offset + 16 + 4        # Row[0] (16 bytes) + leading_zero (4 bytes)
    sizes_base   = offsets_base + entry_count * 4

    offsets = [u32(data, offsets_base + i * 4) for i in range(entry_count)]
    sizes   = [u32(data, sizes_base   + i * 4) for i in range(entry_count)]
    toc_raw = data[toc_offset: sizes_base + entry_count * 4]

    entries = []
    for i in range(entry_count):
        abs_off    = toc_offset + offsets[i]
        entry_data = data[abs_off: abs_off + sizes[i]]
        nested     = None
        if len(entry_data) >= 4 and u32(entry_data, 0) in (1, 3, 0x330):
            try:
                nested = _parse_cat_bytes(entry_data, f"{path}[{i}]")
            except Exception:
                nested = None
        entries.append(ShaderEntry(i, offsets[i], sizes[i], entry_data, nested))

    return CatFile(path, hdr, si, toc_raw, toc_offset, shader_entries=entries)


def _parse_cat_bytes(data: bytes, path: str) -> CatFile:
    hdr = parse_main_header(data)
    if hdr.version == 3:
        return _parse_script_cat(data, path, hdr)
    if hdr.version == 0x330:
        return _parse_story_cat(data, path, hdr)
    if hdr.version != 1:
        print(f"  [WARN] version={hdr.version} (esperado 1)")

    si = parse_section_info(data, hdr.num_sections)
    toc_offset = hdr.toc_offset
    n = hdr.num_sections

    if n == 1:
        return _parse_n1_cat(data, path, hdr, si, toc_offset)

    s0 = _sect0_start(data, toc_offset)
    toc_raw = data[toc_offset: s0]

    if n == 2:
        magic = u32(data, s0)
        if magic == GXT_MAGIC:
            gxt_blocks = _parse_gxt_single(data, s0)
            name_table = parse_name_table(data, si.sect1_start)
            return CatFile(path, hdr, si, toc_raw, s0,
                           gxt_blocks=gxt_blocks, name_table=name_table)
        elif magic == 0:
            scene = parse_scene_section(data, s0, si.sect1_start - s0)
            name_table = parse_name_table(data, si.sect1_start)
            return CatFile(path, hdr, si, toc_raw, s0,
                           scenes=[scene], name_table=name_table)
        else:
            name_table = parse_name_table(data, si.sect1_start)
            return CatFile(path, hdr, si, toc_raw, s0,
                           name_table=name_table)

    if n == 3:
        toc_row0 = struct.unpack_from("<4I", data, toc_offset)
        gxt_sub_count = toc_row0[1]
        toc_subtype   = toc_row0[2]
        gxt_blocks = []
        tmo0_raw = None
        if toc_subtype == 2:
            tmo0_raw = data[s0: si.sect1_start]
        elif gxt_sub_count > 1:
            gxt_blocks = _parse_gxt_multi(data, toc_offset, gxt_sub_count)
        else:
            gxt_blocks = _parse_gxt_single(data, s0)
        scene = parse_scene_section(data, si.sect1_start, si.sect1_size)
        name_table = parse_name_table(data, si.sect2_start)
        return CatFile(path, hdr, si, toc_raw, s0,
                       gxt_blocks=gxt_blocks, tmo0_raw=tmo0_raw,
                       scenes=[scene], name_table=name_table)

    if n == 4:
        magic = u32(data, s0)
        tmd0_raw = None
        tmo0_raw = None
        if magic == TMO0_MAGIC:
            tmo0_raw = data[s0: s0 + si.sect0_size]
        else:
            tmd0_raw = data[s0: s0 + si.sect0_size]
        scenes = [s for s in [
            _try_parse_scene(data, si.sect1_start, si.sect1_size),
            _try_parse_scene(data, si.sect2_start, si.sect2_size),
        ] if s is not None]
        name_table = parse_name_table(data, si.sect3_start)
        return CatFile(path, hdr, si, toc_raw, s0,
                       tmd0_raw=tmd0_raw, tmo0_raw=tmo0_raw,
                       scenes=scenes, name_table=name_table)

    if n == 5:
        tmd0_raw = data[s0: s0 + si.sect0_size]
        scenes = [s for s in [
            _try_parse_scene(data, si.sect1_start, si.sect1_size),
            _try_parse_scene(data, si.sect2_start, si.sect2_size),
            _try_parse_scene(data, si.sect3_start, si.sect3_size),
        ] if s is not None]
        name_table = parse_name_table(data, si.sect4_start)
        return CatFile(path, hdr, si, toc_raw, s0,
                       tmd0_raw=tmd0_raw, scenes=scenes, name_table=name_table)

    # n == 6
    tmd0_raw = data[s0: s0 + si.sect0_size]
    scenes = [s for s in [
        _try_parse_scene(data, si.sect1_start, si.sect1_size),
        _try_parse_scene(data, si.sect2_start, si.sect2_size),
        _try_parse_scene(data, si.sect3_start, si.sect3_size),
        _try_parse_scene(data, si.sect4_start, si.sect4_size),
    ] if s is not None]
    name_table = parse_name_table(data, si.sect5_start)
    return CatFile(path, hdr, si, toc_raw, s0,
                   tmd0_raw=tmd0_raw, scenes=scenes, name_table=name_table)


def parse_cat(path: str) -> CatFile:
    with open(path, "rb") as f:
        data = f.read()
    return _parse_cat_bytes(data, path)


