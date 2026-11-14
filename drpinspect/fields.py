"""Resolve "field list" binary format (used in <FieldsBlob>, <MediaTimemapBA>, nested blobs).

Layout: ver(4) count(4) then per field:
    namelen(4) name(UTF-16BE) type(4) flag(1) value
Types: 1 bool(1B) 2 int32 3 uint32 4/5 int64 6 double 7 float
       0xa string (len(4)+UTF-16BE, -1 = null) 0xc bytes (len(4)+raw, -1 = null)
Big-endian throughout.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Any

T_BOOL, T_I32, T_U32, T_I64A, T_I64B, T_F64, T_F32, T_STR, T_BYTES = 1, 2, 3, 4, 5, 6, 7, 0xA, 0xC


class FieldListError(ValueError):
    pass


@dataclass
class Field:
    name: str
    type: int
    value: Any


def parse(b: bytes) -> list[Field]:
    """Parse a complete field list. Raises FieldListError if the bytes are not exactly one list."""
    if len(b) < 8:
        raise FieldListError("too short")
    ver, n = struct.unpack('>II', b[:8])
    if ver != 1 or n > 100_000:
        raise FieldListError("bad header")
    p = 8
    out: list[Field] = []
    try:
        for _ in range(n):
            L = struct.unpack('>I', b[p:p + 4])[0]
            p += 4
            if L > 4096 or L % 2:
                raise FieldListError("bad name length")
            name = b[p:p + L].decode('utf-16-be')
            p += L
            t = struct.unpack('>I', b[p:p + 4])[0]
            p += 5  # type + flag byte
            if t == T_BOOL:
                val = b[p]; p += 1
            elif t == T_I32:
                val = struct.unpack('>i', b[p:p + 4])[0]; p += 4
            elif t == T_U32:
                val = struct.unpack('>I', b[p:p + 4])[0]; p += 4
            elif t in (T_I64A, T_I64B):
                val = struct.unpack('>q', b[p:p + 8])[0]; p += 8
            elif t == T_F64:
                val = struct.unpack('>d', b[p:p + 8])[0]; p += 8
            elif t == T_F32:
                val = struct.unpack('>f', b[p:p + 4])[0]; p += 4
            elif t == T_STR:
                L = struct.unpack('>i', b[p:p + 4])[0]; p += 4
                if L < 0:
                    val = None
                else:
                    val = b[p:p + L].decode('utf-16-be'); p += L
            elif t == T_BYTES:
                L = struct.unpack('>i', b[p:p + 4])[0]; p += 4
                if L < 0:
                    val = None
                else:
                    if p + L > len(b):
                        raise FieldListError("bytes overrun")
                    val = b[p:p + L]; p += L
            else:
                raise FieldListError(f"unknown type {t:#x} for {name!r}")
            out.append(Field(name, t, val))
    except (struct.error, UnicodeDecodeError, IndexError) as e:
        raise FieldListError(str(e)) from e
    if p != len(b):
        raise FieldListError(f"trailing bytes: {len(b) - p}")
    return out


def serialize(fields: list[Field]) -> bytes:
    out = bytearray(struct.pack('>II', 1, len(fields)))
    for f in fields:
        nb = f.name.encode('utf-16-be')
        out += struct.pack('>I', len(nb)) + nb + struct.pack('>I', f.type) + b'\x00'
        t, val = f.type, f.value
        if t == T_BOOL:
            out += bytes([val])
        elif t == T_I32:
            out += struct.pack('>i', val)
        elif t == T_U32:
            out += struct.pack('>I', val)
        elif t in (T_I64A, T_I64B):
            out += struct.pack('>q', val)
        elif t == T_F64:
            out += struct.pack('>d', val)
        elif t == T_F32:
            out += struct.pack('>f', val)
        elif t == T_STR:
            if val is None:
                out += struct.pack('>i', -1)
            else:
                vb = val.encode('utf-16-be')
                out += struct.pack('>I', len(vb)) + vb
        elif t == T_BYTES:
            if val is None:
                out += struct.pack('>i', -1)
            else:
                out += struct.pack('>I', len(val)) + val
        else:
            raise FieldListError(f"cannot serialize type {t:#x}")
    return bytes(out)


def try_parse(b: bytes) -> list[Field] | None:
    try:
        return parse(b)
    except FieldListError:
        return None
