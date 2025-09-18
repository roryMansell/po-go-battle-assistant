"""Build a compact Pokémon GO dataset with forms & moves.

The source of truth is the public Game Master provided by the PokeMiners
project.  The script ingests the Game Master, expands every form (regional,
costume, shadow, mega, etc.), and emits a trimmed JSON file that the app can
load offline.  Each entry contains the Pokédex number, a friendly name that
includes the form, typing, GO battle stats, and both quick & charged move
lists.

Usage examples:

    # Use the default remote Game Master and write to data/pokemon.min.json
    python scripts/build_pokemon_json.py

    # Use a local Game Master dump and custom output path
    python scripts/build_pokemon_json.py ~/Downloads/latest.json /tmp/out.json
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

GM_URL = "https://raw.githubusercontent.com/PokeMiners/game_masters/master/latest/latest.json"
MOVE_URL = "https://raw.githubusercontent.com/pokemongo-dev-contrib/pokemongo-json-pokedex/master/output/move.json"
DEFAULT_OUT = Path("data/pokemon.min.json")


def log(msg: str) -> None:
    print(f"[build] {msg}")


def load_json(source: str) -> Iterable:
    """Load JSON from a local path or remote URL."""

    if re.match(r"^https?://", source):
        log(f"Downloading {source}")
        with urllib.request.urlopen(source) as resp:  # nosec: trusted hosts
            data = json.load(resp)
        return data

    path = Path(source)
    if path.is_dir():
        # Best effort: look for obvious filenames.
        for name in ("latest.json", "GAME_MASTER.json", "gamemaster.json"):
            candidate = path / name
            if candidate.exists():
                path = candidate
                break
    if not path.exists():
        raise FileNotFoundError(f"Could not find JSON source at {path!s}")
    log(f"Reading {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "pokemon"


def clean_token(token: str) -> str:
    token = token.strip("_").lower()
    if not token:
        return ""
    replacements = {
        "alola": "Alola",
        "alolan": "Alolan",
        "galar": "Galar",
        "galarian": "Galarian",
        "hisui": "Hisui",
        "hisui_an": "Hisuian",
        "mega": "Mega",
        "purified": "Purified",
        "shadow": "Shadow",
        "starter_2022": "Starter 2022",
        "starter_2021": "Starter 2021",
        "standard": "",
        "normal": "",
        "average": "",
        "speed": "Speed",
        "solo": "Solo",
    }
    if token in replacements:
        return replacements[token]
    if token.endswith("_form"):
        return clean_token(token[:-5])
    token = token.replace("gmax", "G-Max")
    if token.isupper():
        return token
    return token.replace("-", " ").title().replace("Hp", "HP").replace("Cp", "CP")


def form_label(pokemon_id: str, form: Optional[str]) -> Optional[str]:
    if not form:
        return None
    if not isinstance(form, str):
        form = str(form)
    # Some entries repeat the base form; skip redundant labels.
    if form.endswith("_NORMAL") or form.endswith("_STANDARD") or form.endswith("_AVERAGE"):
        return None
    suffix = form
    if suffix.startswith(pokemon_id):
        suffix = suffix[len(pokemon_id) :]
    suffix = suffix.strip("_")
    if not suffix:
        return None
    parts = [clean_token(p) for p in suffix.split("_")]
    parts = [p for p in parts if p]
    if not parts:
        return None
    return " ".join(parts)


def format_temp_evo(temp_id: str) -> str:
    suffix = temp_id.replace("TEMP_EVOLUTION_", "")
    parts = [clean_token(p) for p in suffix.split("_")]
    parts = [p for p in parts if p]
    return " ".join(parts) if parts else "Mega"


def format_base_name(pokedex_map: Dict[int, str], dex: int, pokemon_id: str) -> str:
    if dex in pokedex_map:
        return pokedex_map[dex]
    parts = [clean_token(p) for p in pokemon_id.split("_")]
    parts = [p for p in parts if p]
    return " ".join(parts) if parts else pokemon_id.title()


def type_name(enum_value: Optional[str]) -> Optional[str]:
    if not enum_value:
        return None
    return enum_value.replace("POKEMON_TYPE_", "").replace("_", " ").lower()


def move_name(move_id: str, move_map: Dict[str, str]) -> str:
    if not isinstance(move_id, str):
        move_id = str(move_id)
    name = move_map.get(move_id)
    if name:
        name = name.strip()
        # The upstream dataset appends "Fast" to quick moves; keep the word but
        # add parentheses for clarity.
        if name.endswith(" Fast"):
            return f"{name[:-5]} (Fast)"
        return name
    # Fallback: turn the identifier into something readable.
    cleaned = move_id.replace("_FAST", "").replace("_", " ").title()
    return cleaned.replace("Hp", "HP").replace("Cp", "CP")


def load_move_map() -> Dict[str, str]:
    data = load_json(MOVE_URL)
    out: Dict[str, str] = {}
    for entry in data:
        mid = entry.get("id")
        name = entry.get("name")
        if mid and name:
            out[mid] = name
    log(f"Loaded {len(out)} move names")
    return out


def build(dataset: Iterable, move_map: Dict[str, str], pokedex_map: Dict[int, str]) -> List[Dict]:
    output: List[Dict] = []
    seen: set = set()

    def add_entry(
        dex: int,
        base_name: str,
        label: Optional[str],
        key: str,
        types: List[str],
        stats: Dict[str, int],
        fast_moves: Iterable[str],
        charged_moves: Iterable[str],
    ) -> None:
        if not types:
            types = []
        unique_key = (dex, key)
        if unique_key in seen:
            return
        seen.add(unique_key)
        name = base_name if not label else f"{base_name} ({label})"
        entry = OrderedDict(
            {
                "dex": dex,
                "name": name,
                "slug": slugify(name),
                "types": [t for t in types if t],
                "stats": {
                    "attack": stats.get("baseAttack", 0),
                    "defense": stats.get("baseDefense", 0),
                    "stamina": stats.get("baseStamina", 0),
                },
                "moves": {
                    "fast": sorted({move_name(m, move_map) for m in fast_moves if m}),
                    "charged": sorted({move_name(m, move_map) for m in charged_moves if m}),
                },
            }
        )
        output.append(entry)

    for item in dataset:
        settings = item.get("data", {}).get("pokemonSettings")
        if not settings:
            continue
        template_id = item.get("templateId", "")
        m = re.match(r"V(\d{4})_POKEMON_(.+)", template_id)
        if not m:
            continue
        dex = int(m.group(1))
        pokemon_id = settings.get("pokemonId") or m.group(2)
        base_name = format_base_name(pokedex_map, dex, pokemon_id)
        label = form_label(pokemon_id, settings.get("form"))
        types = [type_name(settings.get("type")), type_name(settings.get("type2"))]

        fast_moves = list(settings.get("quickMoves", [])) + list(settings.get("eliteQuickMove", []))
        charged_moves = list(settings.get("cinematicMoves", [])) + list(settings.get("eliteCinematicMove", []))

        add_entry(
            dex,
            base_name,
            label,
            settings.get("form") or "DEFAULT",
            types,
            settings.get("stats", {}),
            fast_moves,
            charged_moves,
        )

        for override in settings.get("tempEvoOverrides", []) or []:
            temp_id = override.get("tempEvoId")
            if not temp_id:
                continue
            otypes = [type_name(override.get("typeOverride1")), type_name(override.get("typeOverride2"))]
            add_entry(
                dex,
                base_name,
                format_temp_evo(temp_id),
                temp_id,
                otypes if any(otypes) else types,
                override.get("stats", settings.get("stats", {})),
                fast_moves,
                charged_moves,
            )

    output.sort(key=lambda row: (row["dex"], row["name"]))
    log(f"Converted {len(output)} entries")
    return output


def load_pokedex_names() -> Dict[int, str]:
    pokedex_path = Path("data/pokedex.json")
    if not pokedex_path.exists():
        return {}
    with pokedex_path.open("r", encoding="utf-8") as fh:
        rows = json.load(fh)
    mapping = {int(row["id"]): row["name"].get("english") for row in rows if row.get("name", {}).get("english")}
    log(f"Loaded {len(mapping)} base Pokédex names")
    return mapping


def main() -> None:
    argv = sys.argv[1:]
    src = argv[0] if argv else GM_URL
    out_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUT

    dataset = load_json(src)
    move_map = load_move_map()
    pokedex_map = load_pokedex_names()

    entries = build(dataset, move_map, pokedex_map)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, separators=(",", ":"))
    log(f"Wrote {len(entries)} Pokémon to {out_path.resolve()}")


if __name__ == "__main__":
    main()
