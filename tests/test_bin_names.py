import io
import zipfile

import pytest

from drpinspect.archive import ArchiveError, read

HEAD = b'<?xml version="1.0" encoding="UTF-8"?>\n<!--DbAppVer="21.1.2.0010" DbPrjVer="17"-->\n<x/>'


def _zip(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as zf:
        for n, d in entries.items():
            zf.writestr(n, d)
    return b.getvalue()


@pytest.mark.parametrize('bin_name', ['001_Bin 2', '000_DA MONTARE', '002_Città (B-roll)', '003_素材'])
def test_real_bin_names(bin_name):
    name = f'MediaPool/Master/{bin_name}/MpFolder.xml'
    assert name in read(_zip({'project.xml': HEAD, name: b'<x/>'})).members


@pytest.mark.parametrize('bad', ['../e.xml', '/a.xml', 'a\\b.xml', 'a/./b.xml', 'a//b.xml', 'C:/x.xml', 'a/b.exe'])
def test_unsafe_names_refused(bad):
    with pytest.raises(ArchiveError):
        read(_zip({'project.xml': HEAD, bad: b'<x/>'}))
