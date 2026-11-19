# The DaVinci Resolve .drp format — field notes

Observed on projects exported from Resolve 19.1.4, 20.3.3 and 21.1.2 (free edition). Not official; Blackmagic documents none of this.

## Container

A `.drp` is a zip (deflate) of UTF-8 XML files:

| Member | Holds |
|---|---|
| `project.xml` | Project settings, project-level data (markers live here, in `Sm2SequenceLockableBlob` records), version header |
| `MediaPool/Master/MpFolder.xml` | The media pool root: clips (`Sm2MpClip`, `Sm2MpVideoClip`, `Sm2MpAudioClip`) and timelines (`Sm2MpTimelineClip`, which carries the timeline's name) |
| `MediaPool/Master/<n>_<Bin>/MpFolder.xml` | One per bin |
| `SeqContainer/<uuid>.xml` | One per timeline: tracks, clips (`Sm2TiVideoClip`, `Sm2TiAudioClip`), transitions (`Sm2TiTransition`), generators/titles/subtitles (`Sm2TiGenerator`), Fusion compositions (`Sm2TiCompositionTable`), per-clip colour grades (`ListMgt::LmVersionTable`) |
| `Gallery.xml` | Stills |

Media is referenced by path, never embedded.

## Version header

Every member begins with a comment:

```
<!--DbAppVer="21.1.2.0010" DbPrjVer="17"-->
```

`DbAppVer` is the Resolve build that wrote the file. `DbPrjVer` is the **project format number**. `project.xml` repeats it as `<ProjectVersion>`. Resolve refuses to import a file whose format number is higher than its own and offers an upgrade for lower ones.

| DbPrjVer | Seen in |
|---|---|
| 14 | Resolve 19.1.4 |
| 15 | Resolve 20.3.3 |
| 16 | not observed (presumably 21.0 / 21.1.0) |
| 17 | Resolve 21.1.2 |

Minor releases can bump it (Blackmagic's forum records 18.5 projects refusing to open in 18.1). Patch releases usually don't.

Tag names use `::` (e.g. `ListMgt::LmVersionTable`), which strict XML parsers reject; treat the files as text.

## Binary blobs

Most detail is not plain XML but hex strings in elements such as `<FieldsBlob>`, `<MediaTimemapBA>`, `<Body>`.

**Field list** (`FieldsBlob` and friends), big-endian:

```
u32 version (=1)   u32 count
per field: u32 namelen, name (UTF-16BE), u32 type, u8 flag, value
types: 1 bool(u8)  2 i32  3 u32  4/5 i64  6 f64  7 f32
       0xA string (i32 len + UTF-16BE; -1 = null)   0xC bytes (i32 len + raw; -1 = null)
```

Large byte values are wrapped: `00000001 <u32 len> <marker> <payload>`. Marker `81` means the payload is a zstd frame; marker `80` means it is stored uncompressed (Resolve uses this for small values, e.g. `MpWidgetsSelectionDataBA` in 19.1.4 and short retime curves in 21.1.1). Either way the payload is a Protocol Buffers message (settings, clip properties). Retime keyframes in 21 (`KeyframesBA`) use the same two markers without the 8-byte prefix. Per-clip grades (`LmVersion/Body`) are `81 <zstd frame>` holding a protobuf node graph whose parameters are `(id, float32)` pairs.

## Differences between versions

Between 19, 20 and 21 the XML structure is almost identical: the same elements, in the same places. What changes: the header and format number, a few feature flags, a handful of extra settings fields, a couple of empty container elements, and, in 21, the storage format of speed-change keyframes. The grade node graph is stored identically across all three. That is why conversion between versions is possible; it is what [filedowngrade.com](https://filedowngrade.com) does.

Media Pool bins appear as folders named after the bin, so member names contain whatever the editor typed: spaces (`MediaPool/Master/001_Bin 2/MpFolder.xml`), accents or non-Latin text. Resolve writes these names as UTF-8 without setting the zip's UTF-8 flag.
