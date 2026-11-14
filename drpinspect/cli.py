import argparse
import json
import sys
from pathlib import Path

from .archive import read, ArchiveError
from .inspect import inspect, format_text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='drp-inspect', description='Report which DaVinci Resolve version saved a .drp and what it contains.')
    ap.add_argument('file', help='path to a .drp (Project Manager → Export Project)')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    a = ap.parse_args(argv)
    try:
        r = inspect(read(Path(a.file).read_bytes()))
    except FileNotFoundError:
        print(f"not found: {a.file}", file=sys.stderr)
        return 2
    except ArchiveError as e:
        print(f"not a readable .drp: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r.to_dict(), indent=1) if a.json else format_text(r))
    return 0


if __name__ == '__main__':
    sys.exit(main())
