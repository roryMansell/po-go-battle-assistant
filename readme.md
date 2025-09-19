# 🎙️ Voice Pokédex — Offline Team Assistant  

An **offline Pokédex web app** that listens to your voice, shows **type weaknesses/resistances**, and ranks your chosen team of Pokémon against opponents.  
Built with **HTML/CSS/JS**, powered by **local JSON + sprites**, and completely offline once set up.

---

## ✨ Features
- 🎤 **Voice recognition** (Web Speech API) — say a Pokémon’s name to instantly fetch its info. (Not avaialble in desktop build) 
- ⌨️ **Fallback search** — type or pick from a dropdown.  
- 🧩 **Type matchups** — see weaknesses, resistances, and immunities using a Gen-9 style type chart.  
- 🖼 **Sprites included offline** — official artwork and in-game sprites packaged locally.  
- 👥 **Team builder** — choose up to 3 Pokémon; their matchups are ranked against the selected opponent.  
- 💻 **Completely offline** — no API calls, works without internet once installed.  

---

## 🌍 Live Demo
The app can be run entirely in your browser (hosted on GitHub Pages):

👉 [**Open Live Pokédex**](https://roryMansell.github.io/po-go-battle-assistant/)  

> ⚠️ Voice input requires **HTTPS** (works in Chrome/Edge). Desktop builds run fully offline but disable voice search.

## 🖼️ Screenshots
![Screenshot](demoPNG.png)
![GIF Demo](demo-gif.gif)
---

## 🚀 Running the App

This is a **static site** (HTML, CSS, JS, JSON). To run it locally:

```bash
cd po-go-battle-assistant
python -m http.server 8000
```
Then open:

👉 http://localhost:8000/index.html

## 🖥️ Download

- [Installer (recommended)](https://github.com/roryMansell/po-go-battle-assistant/releases/latest/download/Voice.Pokedex.Setup.1.0.0.exe)
- [Portable (no install)](https://github.com/roryMansell/po-go-battle-assistant/releases/latest/download/VoicePokedex-win64.zip)

## Languages and technologies

Frontend: HTML, CSS, JavaScript (interactive UI, offline data handling, voice input)

Data prep: Python (scripts for JSON + sprite processing)

Desktop packaging: Electron (Node.js ecosystem)

## 📦 Updating the Pokémon GO dataset

The app reads from `data/pokemon.min.json`. To refresh the data (all Pokémon, forms, and available moves straight from the latest Game Master), run:

```bash
python scripts/build_pokemon_json.py
```

The script downloads the current Game Master from the PokeMiners project, expands every form (regional, costume, mega, shadow, etc.), and writes a compact JSON file ready for offline use.

## 📜 License

Data & sprites belong to their respective creators (Pokémon © Nintendo/Game Freak).

This project is for educational and portfolio use only.

