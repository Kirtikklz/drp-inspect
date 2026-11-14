import io, sys, zipfile
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drpinspect.archive import read, ArchiveError
from drpinspect.inspect import inspect, format_text
from drpinspect.cli import main

HDR = '<!--DbAppVer="20.3.3.0010" DbPrjVer="15"-->\n'


def sample() -> bytes:
    proj = HDR + '<SM_Project DbId="p"><ProjectVersion>15</ProjectVersion></SM_Project>'
    mp = HDR + ('<Sm2MpFolder DbId="f"><Sm2MpVideoClip DbId="a"><Name>vid1.mp4</Name></Sm2MpVideoClip>'
                '<Sm2MpTimelineClip DbId="t"><FieldsBlob/><PrettyType>Timeline</PrettyType><Name>Timeline 1</Name></Sm2MpTimelineClip></Sm2MpFolder>')
    seq = HDR + ('<Sm2SequenceContainer DbId="s"><Sm2TiVideoClip DbId="c1"><MediaTimemapBA>' + 'ab' * 30 + '</MediaTimemapBA></Sm2TiVideoClip>'
                 '<Sm2TiVideoClip DbId="c2"><ListMgt::LmVersionTable DbId="l"/></Sm2TiVideoClip><Sm2TiAudioClip DbId="a1"/>'
                 '<Sm2TiTransition DbId="x"/><Sm2TiGenerator DbId="g"/></Sm2SequenceContainer>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('project.xml', proj); z.writestr('MediaPool/Master/MpFolder.xml', mp)
        z.writestr('SeqContainer/abc.xml', seq); z.writestr('Gallery.xml', HDR + '<Gallery/>')
    return buf.getvalue()


def test_inspect_counts():
    r = inspect(read(sample()))
    assert r.app_version == '20.3.3.0010' and r.format_number == 15 and 'Resolve 20' in r.format_label
    assert r.timeline_names == ['Timeline 1'] and r.media_clips == 1
    s = r.sequences[0]
    assert (s.video_clips, s.audio_clips, s.transitions, s.generators, s.graded_clips, s.speed_changes) == (2, 1, 1, 1, 1, 1)
    assert 'Saved with' in format_text(r)


def test_rejects_garbage_and_traversal():
    with pytest.raises(ArchiveError):
        read(b'nope')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('../x.xml', '<a/>'); z.writestr('project.xml', HDR + '<a/>')
    with pytest.raises(ArchiveError):
        read(buf.getvalue())


def test_cli(tmp_path, capsys):
    p = tmp_path / 's.drp'; p.write_bytes(sample())
    assert main([str(p)]) == 0 and 'Saved with' in capsys.readouterr().out
    assert main([str(p), '--json']) == 0
    assert main([str(tmp_path / 'missing.drp')]) == 2
