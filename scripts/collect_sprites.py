import re, shutil, sys
from pathlib import Path

# Usage:
#   python scripts/collect_sprites.py /path/to/PokeAPI/sprites <optional_output_dir>
# Example:
#   python scripts/collect_sprites.py ../sprites-repo ./sprites
#
# Works if you pass either the repo root (which contains "sprites/")
# OR the sprites folder itself (which contains "pokemon/").

SRC_IN = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('sprites')

if not SRC_IN or not SRC_IN.exists():
    print('Provide path to cloned https://github.com/PokeAPI/sprites repository (root or its "sprites" folder).')
    sys.exit(1)

# Resolve where the 'pokemon' folder is
def find_dirs(base: Path):
    # Case A: repo root .../sprites-repo (expect base/sprites/pokemon)
    a_official = base / 'sprites' / 'pokemon' / 'other' / 'official-artwork'
    a_front    = base / 'sprites' / 'pokemon'
    # Case B: passed .../sprites-repo/sprites (expect base/pokemon)
    b_official = base / 'pokemon' / 'other' / 'official-artwork'
    b_front    = base / 'pokemon'

    if a_front.exists():
        return a_official, a_front
    if b_front.exists():
        return b_official, b_front
    return None, None

OFFICIAL, FRONT = find_dirs(SRC_IN)
if OFFICIAL is None:
    print(f"Couldn't find 'pokemon' sprites under: {SRC_IN}")
    print("Make sure the path is either the repo root or its 'sprites' directory.")
    sys.exit(1)

OUT.mkdir(parents=True, exist_ok=True)

ids = set()
num = re.compile(r'^(\d+)\.png$')  # <-- fixed regex

def collect_ids(dirpath: Path):
    try:
        for p in dirpath.iterdir():
            m = num.match(p.name)
            if m:
                ids.add(int(m.group(1)))
    except FileNotFoundError:
        pass

collect_ids(OFFICIAL)
collect_ids(FRONT)

print(f'Found {len(ids)} candidate sprites. OFFICIAL={"yes" if OFFICIAL.exists() else "no"}, FRONT={"yes" if FRONT.exists() else "no"}')

picked = 0
for i in sorted(ids):
    src = OFFICIAL / f'{i}.png'
    if not src.exists():
        src = FRONT / f'{i}.png'
    if not src.exists():
        continue

    name = f'{i:03d}.png' if i < 1000 else f'{i}.png'
    dst = OUT / name
    shutil.copyfile(src, dst)
    picked += 1

print(f'Wrote {picked} sprites to {OUT.resolve()}')
