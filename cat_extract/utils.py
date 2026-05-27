import struct


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]

def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]

def read_pstring(data: bytes, offset: int) -> tuple[str, int]:
    length = data[offset]
    text = data[offset + 1: offset + 1 + length].decode("ascii", errors="replace")
    return text, offset + 1 + length

def read_vec3(data: bytes, offset: int) -> tuple[tuple[float, float, float], int]:
    x = f32(data, offset)
    y = f32(data, offset + 4)
    z = f32(data, offset + 8)
    return (x, y, z), offset + 12
