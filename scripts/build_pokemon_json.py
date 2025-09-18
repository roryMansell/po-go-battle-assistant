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
PVP_RANKING_URLS = [
    "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/rankings/all/overall/rankings-1500.json",
    "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/rankings/all/overall/rankings-2500.json",
    "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/rankings/all/overall/rankings-10000.json",
    "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/rankings/all/overall/rankings-500.json",
]
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


def move_name(move_id: str, move_map: Dict[str, Dict[str, object]]) -> str:
    if not isinstance(move_id, str):
        move_id = str(move_id)
    info = move_map.get(move_id)
    if info:
        name = str(info.get("name") or "").strip()
        if name:
            return name
    # Fallback: turn the identifier into something readable.
    cleaned = move_id.replace("_FAST", "").replace("_", " ").title()
    return cleaned.replace("Hp", "HP").replace("Cp", "CP")


def load_move_map() -> Dict[str, Dict[str, object]]:
    data = load_json(MOVE_URL)
    out: Dict[str, Dict[str, object]] = {}
    for entry in data:
        mid = entry.get("id")
        if not mid:
            continue
        raw_name = (entry.get("name") or "").strip()
        energy = int(entry.get("energyDelta") or 0)
        duration_ms = int(entry.get("durationMs") or 0)
        power = int(entry.get("power") or 0)
        cooldown_s = duration_ms / 1000 if duration_ms else None
        turns = duration_ms / 500 if duration_ms else None
        category = "fast" if energy > 0 else "charged"
        move_type = type_name((entry.get("pokemonType") or {}).get("name"))
        name = raw_name or mid.replace("_", " ").title()
        if category == "fast":
            if name.endswith(" Fast"):
                name = name[:-5]
            if not name.endswith("(Fast)"):
                name = f"{name} (Fast)"
        dps = power / cooldown_s if cooldown_s else None
        eps = energy / cooldown_s if cooldown_s else None
        dpe = power / abs(energy) if energy and category == "charged" else None
        out[mid] = {
            "id": mid,
            "name": name,
            "type": move_type,
            "power": power,
            "energy": energy,
            "duration_ms": duration_ms,
            "cooldown_s": cooldown_s,
            "turns": turns,
            "category": category,
            "dps": dps,
            "eps": eps,
            "dpe": dpe,
        }
    log(f"Loaded {len(out)} move definitions")
    return out


def load_pvpoke_movesets() -> Dict[str, Dict[str, List[str]]]:
    """Fetch recommended movesets from PvPoke rankings."""

    combos: Dict[str, Dict[str, List[str]]] = {}
    for url in PVP_RANKING_URLS:
        try:
            rows = load_json(url)
        except Exception as exc:  # pragma: no cover - network failure fallback
            log(f"Warning: could not load {url}: {exc}")
            continue
        added = 0
        for row in rows or []:
            species_id = row.get("speciesId")
            moveset = row.get("moveset")
            if not species_id or not moveset or len(moveset) < 3:
                continue
            slug = species_id.replace("_", "-")
            if slug in combos:
                continue
            combos[slug] = {
                "fast": [moveset[0]],
                "charged": list(moveset[1:3]),
            }
            added += 1
        log(f"Loaded {added} PvPoke movesets from {url}")
    return combos


def build(
    dataset: Iterable,
    move_map: Dict[str, Dict[str, object]],
    pokedex_map: Dict[int, str],
    recommended_map: Dict[str, Dict[str, List[str]]],
) -> List[Dict]:
    output: List[Dict] = []
    seen: set = set()

    def format_moves(move_ids: Iterable[str]) -> List[OrderedDict]:
        seen_ids: set = set()
        entries: List[OrderedDict] = []
        for mid in move_ids:
            if not mid or mid in seen_ids:
                continue
            seen_ids.add(mid)
            info = move_map.get(mid)
            if info:
                entry = OrderedDict(
                    {
                        "id": info["id"],
                        "name": info["name"],
                        "type": info.get("type"),
                        "category": info.get("category"),
                        "power": info.get("power"),
                        "energy": info.get("energy"),
                    }
                )
                if info.get("cooldown_s") is not None:
                    entry["cooldown"] = round(info["cooldown_s"], 2)
                if info.get("turns") is not None:
                    entry["turns"] = round(info["turns"], 2)
                if info.get("dps") is not None:
                    entry["dps"] = round(info["dps"], 2)
                if info.get("eps") is not None:
                    entry["eps"] = round(info["eps"], 2)
                if info.get("dpe") is not None:
                    entry["dpe"] = round(info["dpe"], 2)
            else:
                entry = OrderedDict({"id": mid, "name": move_name(mid, move_map)})
            entries.append(entry)
        entries.sort(key=lambda row: row.get("name", ""))
        return entries

    def match_ids(moves: List[OrderedDict], candidates: Iterable[str]) -> Optional[List[str]]:
        resolved: List[str] = []
        for cand in candidates:
            if not cand:
                continue
            target = str(cand).upper()
            for mv in moves:
                mid = str(mv.get("id") or "").upper()
                if not mid:
                    continue
                normalized = mid.replace("_FAST", "")
                if mid == target or normalized == target or f"{target}_FAST" == mid:
                    resolved.append(mv.get("id"))
                    break
        return resolved or None

    def find_recommended(slug: str, fast_list: List[OrderedDict], charged_list: List[OrderedDict]) -> Optional[Dict[str, object]]:
        rec = recommended_map.get(slug)
        if not rec:
            return None
        out: Dict[str, object] = {}
        fast_candidates = rec.get("fast", [])
        charged_candidates = rec.get("charged", [])
        if fast_candidates:
            fast_matches = match_ids(fast_list, fast_candidates)
            if fast_matches:
                out["fast"] = fast_matches[0]
        if charged_candidates:
            charged_matches = match_ids(charged_list, charged_candidates)
            if charged_matches:
                out["charged"] = charged_matches
        return out or None

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
        slug = slugify(name)
        fast_list = format_moves(fast_moves)
        charged_list = format_moves(charged_moves)
        moves = OrderedDict({
            "fast": fast_list,
            "charged": charged_list,
        })
        recommended = find_recommended(slug, fast_list, charged_list)
        if recommended:
            moves["recommended"] = recommended
        entry = OrderedDict(
            {
                "dex": dex,
                "name": name,
                "slug": slug,
                "types": [t for t in types if t],
                "stats": {
                    "attack": stats.get("baseAttack", 0),
                    "defense": stats.get("baseDefense", 0),
                    "stamina": stats.get("baseStamina", 0),
                },
                "moves": moves,
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
    recommended_map = load_pvpoke_movesets()

    entries = build(dataset, move_map, pokedex_map, recommended_map)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, separators=(",", ":"))
    log(f"Wrote {len(entries)} Pokémon to {out_path.resolve()}")


if __name__ == "__main__":
    main()
