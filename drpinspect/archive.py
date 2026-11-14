"""Safe reading/writing of .drp archives (zip of XML text files).

A .drp from a stranger is untrusted. We never trust member names, never extract to disk,
cap sizes and counts, and only keep members that are plain XML text.
"""
from __future__ import annotations
import io
import re
import zipfile
import zlib
from dataclasses import dataclass, field


class ArchiveError(ValueError):
    pass


@dataclass
class Limits:
    max_members: int = 400
    max_member_bytes: int = 200 << 20       # one XML file
    max_total_bytes: int = 600 << 20        # all members unpacked
    max_ratio: int = 200                    # unpacked/packed, zip-bomb guard


SAFE_NAME = re.compile(r'^(?:[A-Za-z0-9_\-]+/)*[A-Za-z0-9_\-]+\.xml$')
HEADER = re.compile(r'<!--DbAppVer="([^"]+)" DbPrjVer="(\d+)"-->')


@dataclass
class Drp:
    members: dict[str, str] = field(default_factory=dict)   # name -> xml text, in zip order
    dates: dict[str, tuple] = field(default_factory=dict)

    @property
    def names(self) -> list[str]:
        return list(self.members)


def read(data: bytes, limits: Limits = Limits()) -> Drp:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ArchiveError("not a zip file") from e
    infos = zf.infolist()
    if not infos:
        raise ArchiveError("empty archive")
    if len(infos) > limits.max_members:
        raise ArchiveError(f"too many files in archive ({len(infos)})")
    drp = Drp()
    total = 0
    for info in infos:
        name = info.filename
        if name.endswith('/'):
            continue  # directory entry
        if not SAFE_NAME.match(name) or '..' in name:
            raise ArchiveError(f"unexpected file in archive: {name[:80]!r}")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ArchiveError("unsupported compression")
        if info.file_size > limits.max_member_bytes:
            raise ArchiveError("a file inside the archive is too large")
        if info.compress_size and info.file_size / max(info.compress_size, 1) > limits.max_ratio and info.file_size > (1 << 20):
            raise ArchiveError("suspicious compression ratio")
        total += info.file_size
        if total > limits.max_total_bytes:
            raise ArchiveError("archive unpacks to too much data")
        # read with a hard cap regardless of what the header claims
        try:
            with zf.open(info) as fh:
                raw = fh.read(limits.max_member_bytes + 1)
        except (zipfile.BadZipFile, zlib.error, EOFError, OSError, RuntimeError, NotImplementedError, ValueError) as e:
            raise ArchiveError(f"archive is damaged ({name} cannot be read)") from e
        if len(raw) > limits.max_member_bytes:
            raise ArchiveError("a file inside the archive is too large")
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ArchiveError(f"{name} is not UTF-8 text") from e
        if '\x00' in text or not text.lstrip().startswith('<'):
            raise ArchiveError(f"{name} is not XML")
        if not balanced(text):
            raise ArchiveError(f"{name} is damaged (XML is cut off or unbalanced)")
        drp.members[name] = text
        drp.dates[name] = info.date_time
    if 'project.xml' not in drp.members:
        raise ArchiveError("not a DaVinci Resolve project (no project.xml)")
    if not HEADER.search(drp.members['project.xml']):
        raise ArchiveError("not a DaVinci Resolve project (no version header)")
    return drp


TAG = re.compile(r'<(/?)([A-Za-z_][\w:.\-]*)[^<>]*?(/?)>|<!--.*?-->|<\?.*?\?>', re.S)


def balanced(text: str) -> bool:
    """Cheap well-formedness check: every opened element is closed, in order. Resolve's
    files use '::' in tag names, which strict XML parsers reject, so we do it ourselves."""
    stack: list[str] = []
    for m in TAG.finditer(text):
        if m.group(2) is None:
            continue  # comment or processing instruction
        closing, name, selfclose = m.group(1), m.group(2), m.group(3)
        if closing:
            if not stack or stack[-1] != name:
                return False
            stack.pop()
        elif not selfclose:
            stack.append(name)
    # anything outside tags must be whitespace or text content; a cut-off file leaves the stack open
    return not stack


def write(drp: Drp) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, text in drp.members.items():
            zi = zipfile.ZipInfo(name, date_time=drp.dates.get(name, (2026, 1, 1, 0, 0, 0)))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, text.encode('utf-8'))
    return buf.getvalue()


def header_of(drp: Drp) -> tuple[str, int]:
    m = HEADER.search(drp.members['project.xml'])
    return m.group(1), int(m.group(2))
