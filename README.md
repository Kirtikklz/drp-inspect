# drp-inspect

Which DaVinci Resolve version saved this project file, and what's in it — without opening Resolve.

When Resolve says **"Unable to Import Project. A newer version of DaVinci Resolve is needed to import this project"**, the first useful fact is *which* version wrote the file. Resolve won't tell you. The file will.

```
$ drp-inspect myproject.drp
Saved with    DaVinci Resolve 21.1.2.0010  (project format 17: DaVinci Resolve 21.1+)
Opens in      Resolve versions with format >= 17; older versions refuse it
Files         7 XML members, 1 bin(s)
Media clips   2
Timelines     Timeline 1, Timeline 2
Clips         7 video, 5 audio
Transitions   2
Generators    1 (titles, subtitles)
Fusion comps  1
Graded clips  1
Speed changes 1
Marker blocks 1
```

`--json` gives the same as machine-readable output.

## Install

```
pipx install git+https://github.com/Kirtikklz/drp-inspect
# or
pip install git+https://github.com/Kirtikklz/drp-inspect
```

Python 3.10+, no dependencies. Nothing is uploaded anywhere; it reads the file locally.

## What a .drp is

A `.drp` (Project Manager → Export Project) is a zip archive of XML files. See [FORMAT.md](FORMAT.md) for what each member holds, how the version header works, and the project format numbers we've observed (14 = Resolve 19, 15 = Resolve 20, 17 = Resolve 21.1).

This tool only reads. It deliberately refuses anything that isn't a plain-XML zip, caps sizes, and never executes or extracts anything from the file.

## Need to open it in an older Resolve?

Resolve has no "save for older version". The file can be converted: [filedowngrade.com](https://filedowngrade.com) rewrites the version markers and newer-only settings so Resolve 20 or 19 imports it, with the edit, grades, titles, keyframes, audio and subtitles intact. The free report there is this tool's output plus a check of what the older version can hold.

## Licence

MIT. Not affiliated with Blackmagic Design; DaVinci Resolve is their trademark.
