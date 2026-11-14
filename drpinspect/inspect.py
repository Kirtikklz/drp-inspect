"""Report on a .drp without opening Resolve: which version saved it, and what it contains."""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict

from .archive import Drp, HEADER

# Project format numbers observed in exported files. Resolve refuses to import a file whose
# format number is higher than its own.
FORMATS = {14: 'DaVinci Resolve 19', 15: 'DaVinci Resolve 20', 17: 'DaVinci Resolve 21.1+'}


@dataclass
class Sequence:
    video_clips: int = 0
    audio_clips: int = 0
    generators: int = 0          # titles, subtitles and other generators
    transitions: int = 0
    graded_clips: int = 0
    speed_changes: int = 0
    fusion_comps: int = 0


@dataclass
class Report:
    app_version: str
    format_number: int
    format_label: str
    files: int
    bins: int
    media_clips: int
    timeline_names: list[str]
    sequences: list[Sequence]
    marker_blocks: int

    def to_dict(self) -> dict:
        return asdict(self)


def _scan_sequence(text: str) -> Sequence:
    sq = Sequence()
    sq.video_clips = len(re.findall(r'<Sm2TiVideoClip DbId', text))
    sq.audio_clips = len(re.findall(r'<Sm2TiAudioClip DbId', text))
    sq.generators = len(re.findall(r'<Sm2TiGenerator DbId', text))
    sq.transitions = len(re.findall(r'<Sm2TiTransition DbId', text))
    sq.graded_clips = len(re.findall(r'<ListMgt::LmVersionTable DbId', text))
    sq.speed_changes = sum(1 for c in re.findall(r'<Sm2TiVideoClip DbId="[^"]+">(.*?)</Sm2TiVideoClip>', text, re.S)
                           if re.search(r'<MediaTimemapBA>[0-9a-f]{40,}</MediaTimemapBA>', c))
    sq.fusion_comps = len(re.findall(r'<Sm2TiCompositionTable DbId', text))
    return sq


def inspect(drp: Drp) -> Report:
    app, prj = HEADER.search(drp.members['project.xml']).groups()
    prj = int(prj)
    names: list[str] = []
    seqs: list[Sequence] = []
    media = 0
    markers = 0
    for name, text in drp.members.items():
        if name == 'project.xml':
            markers = sum(1 for b in re.findall(r'<Sm2SequenceLockableBlob DbId="[^"]+">\s*<FieldsBlob>([0-9a-f]+)</FieldsBlob>', text) if len(b) > 60)
        if name.endswith('MpFolder.xml'):
            media += len(re.findall(r'<Sm2MpClip DbId', text)) + len(re.findall(r'<Sm2MpVideoClip DbId', text)) + len(re.findall(r'<Sm2MpAudioClip DbId', text))
            for mm in re.finditer(r'<Sm2MpTimelineClip DbId="[^"]+">\s*<FieldsBlob[^>]*>(?:[0-9a-f]*</FieldsBlob>)?\s*(?:<PrettyType>[^<]*</PrettyType>\s*)?<Name>([^<]*)</Name>', text):
                names.append(mm.group(1))
        if name.startswith('SeqContainer/'):
            seqs.append(_scan_sequence(text))
    bins = sum(1 for n in drp.members if n.endswith('MpFolder.xml')) - 1
    label = FORMATS.get(prj, f'unknown format {prj} (newer than this tool knows)')
    return Report(app_version=app, format_number=prj, format_label=label, files=len(drp.members),
                  bins=max(bins, 0), media_clips=media, timeline_names=names, sequences=seqs, marker_blocks=markers)


def format_text(r: Report) -> str:
    tot = lambda k: sum(getattr(s, k) for s in r.sequences)  # noqa: E731
    lines = [
        f"Saved with    DaVinci Resolve {r.app_version}  (project format {r.format_number}: {r.format_label})",
        f"Opens in      Resolve versions with format >= {r.format_number}; older versions refuse it",
        f"Files         {r.files} XML members, {r.bins} bin(s)",
        f"Media clips   {r.media_clips}",
        f"Timelines     {', '.join(r.timeline_names) if r.timeline_names else len(r.sequences)}",
        f"Clips         {tot('video_clips')} video, {tot('audio_clips')} audio",
        f"Transitions   {tot('transitions')}",
        f"Generators    {tot('generators')} (titles, subtitles)",
        f"Fusion comps  {tot('fusion_comps')}",
        f"Graded clips  {tot('graded_clips')}",
        f"Speed changes {tot('speed_changes')}",
        f"Marker blocks {r.marker_blocks}",
    ]
    return "\n".join(lines)
