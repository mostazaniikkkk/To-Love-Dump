from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MainHeader:
    version: int
    num_sections: int
    reserved: int
    toc_offset: int


@dataclass
class SectionInfo1:
    data_size: int
    field1: int
    entry_count: int
    padding: int


@dataclass
class SectionInfo2:
    sect1_start: int
    sect0_size: int
    sect1_size: int
    count_scene_items: int
    count_unk: int
    type_table_count: int
    unk: int
    padding: int


@dataclass
class SectionInfo3:
    sect1_start: int
    sect2_start: int
    sect0_size: int
    sect1_size: int
    sect2_size: int
    gxt_tex_count: int
    count_scene_items: int
    count_unk: int
    unk0: int
    type_table_count: int
    unk1: int
    padding: int


@dataclass
class SectionInfo4:
    sect1_start: int
    sect2_start: int
    sect3_start: int
    sect0_size: int
    sect1_size: int
    sect2_size: int
    sect3_size: int
    padding: int
    unk: int
    count_scene_items: int
    count_unk: int
    unk2: int
    num_sections_echo: int
    type_table_count: int
    unk3: int
    padding2: int


@dataclass
class SectionInfo5:
    sect1_start: int
    sect2_start: int
    sect3_start: int
    sect4_start: int
    sect0_size: int
    sect1_size: int
    sect2_size: int
    sect3_size: int
    sect4_size: int
    padding: int
    unk: int
    count_scene_items: int
    count_unk: int
    count_unk2: int
    unk2: int
    unk3: int
    unk4: int
    type_table_count: int
    unk5: int
    padding2: int


@dataclass
class SectionInfo6:
    sect1_start: int
    sect2_start: int
    sect3_start: int
    sect4_start: int
    sect5_start: int
    sect0_size: int
    sect1_size: int
    sect2_size: int
    sect3_size: int
    sect4_size: int
    sect5_size: int
    padding: int
    unk_var: int
    unk0: int
    unk1: int
    count_scene_items: int
    count_unk: int
    unk2: int
    unk3: int
    unk4: int
    unk5: int
    unk6: int
    unk7: int
    padding2: int


@dataclass
class GxtHeader:
    magic: int
    version: int
    num_textures: int
    header_size: int   # 0x20 + num_textures * 0x20
    data_size: int
    num_p4_tex: int
    num_p8_tex: int
    pad: int


@dataclass
class GxtTexture:
    data_offset: int
    data_size: int
    palette_index: int
    flags: int
    type: int
    base_level_size: int
    width: int
    height: int
    tex_format: int    # at +0x1C; no mip_mask (descriptor is exactly 0x20 bytes)


@dataclass
class GxtBlock:
    header: GxtHeader
    textures: list     # list[GxtTexture]
    data: bytes


@dataclass
class SceneObject:
    name: str
    position: tuple
    scale: tuple
    rotation: tuple
    obj_type: str
    extra_raw: bytes = field(default_factory=bytes)


@dataclass
class SceneData:
    scene_name: str
    version: int
    objects: list = field(default_factory=list)
    sub_blocks_raw: list = field(default_factory=list)


@dataclass
class ScriptEntry:
    index: int
    offset: int     # relativo a toc_offset
    size: int       # tamaño del cuerpo (sin filename)
    end: int        # relativo a toc_offset; posición del filename de 16 bytes
    magic: int      # 0x534D4154 = TAMS; 0 = filename-only
    body: bytes
    filename: str   # ASCII, null-stripped


@dataclass
class ShaderEntry:
    index: int
    offset: int      # relativo a toc_offset
    size: int
    data: bytes
    nested_cat: Optional[object] = None  # CatFile si la entry es un CAT anidado


@dataclass
class CatFile:
    path: str
    header: MainHeader
    section_info: object
    toc_raw: bytes
    sect0_start: int
    gxt_blocks: list = field(default_factory=list)    # list[GxtBlock]
    tmd0_raw: Optional[bytes] = None
    tmo0_raw: Optional[bytes] = None
    scenes: list = field(default_factory=list)         # list[SceneData]
    name_table: list = field(default_factory=list)
    script_entries: list = field(default_factory=list)  # list[ScriptEntry] (version=3)
    shader_entries: list = field(default_factory=list)  # list[ShaderEntry] (num_sections=1)
