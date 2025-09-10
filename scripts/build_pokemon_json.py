import json, sys
from pathlib import Path

def log(msg): print(f"[build] {msg}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/build_pokemon_json.py <path-to-pokedex.json-or-folder> <output(optional)>")
        sys.exit(1)

    src_arg = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/pokemon.min.json")

    log(f"cwd = {Path.cwd()}")
    log(f"src_arg = {src_arg}  (exists={src_arg.exists()})")
    log(f"out_path = {out_path}")

    if not src_arg.exists():
        print(f"ERROR: Source path does not exist: {src_arg}")
        sys.exit(1)

    # If you passed the folder, append pokedex.json
    src_file = src_arg / "pokedex.json" if src_arg.is_dir() else src_arg
    log(f"src_file = {src_file}  (exists={src_file.exists()})")
    if not src_file.exists():
        print(f"ERROR: Could not find pokedex.json at: {src_file}")
        sys.exit(1)

    # Read source
    with src_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("ERROR: pokedex.json didn't parse as a list.")
        sys.exit(1)
    log(f"source entries = {len(data)}")

    def norm_type(t: str) -> str: return t.strip().lower()

    def convert(entry):
        return {
            "id": int(entry["id"]),
            "name": str(entry["name"]["english"]),
            "types": [norm_type(t) for t in entry["type"]],
            "stats": {
                "hp": int(entry["base"]["HP"]),
                "atk": int(entry["base"]["Attack"]),
                "def": int(entry["base"]["Defense"]),
                "spa": int(entry["base"]["Sp. Attack"]),
                "spd": int(entry["base"]["Sp. Defense"]),
                "spe": int(entry["base"]["Speed"]),
            },
        }

    out = [convert(e) for e in data]
    out.sort(key=lambda x: x["id"])
    log(f"converted entries = {len(out)}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))

    print(f"Wrote {len(out)} Pokémon to {out_path.resolve()}")

if __name__ == "__main__":
    main()
