# -*- coding: utf-8 -*-
"""
Pesquisa e baixa retratos de jogadores do CBLOL a partir do lol.fandom (Leaguepedia).

- Prefere fotos reais de time (não Square de campeão, não logos).
- Gera frontend/src/lib/playerPhotoMap.ts com mapeamento nick -> /players/{slug}.jpg
- Onde não achar foto, omite a chave (UI usa silhueta).

Uso (na raiz do projeto):
  PYTHONPATH=. venv/Scripts/python scripts/fetch_player_photos.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "public" / "players"
MAP_TS = ROOT / "frontend" / "src" / "lib" / "playerPhotoMap.ts"
META_JSON = ROOT / "frontend" / "public" / "players" / "_meta.json"

UA = "MobaManagerPhotoBot/1.0 (personal offline game; +https://localhost)"

# Páginas Leaguepedia quando o nick sozinho é ambíguo
PAGE_OVERRIDES = {
    "Tatu": "Tatu_(Pedro_Seixas)",
    "Kaze": "Kaze_(Lucas_Fe)",
    "JoJo": "JoJo_(Gabriel_Dzelme)",
    "Ayu": "Ayu",
    "Envy": "Envy",
    "Bull": "Bull",
    "ceo": "Ceo",
    "Zest": "Zest_(Kim_Dong-min)",
    "Peach": "Peach_(Korean_player)",
    "BAO": "BAO_(Jeong_Hyeon-woo)",
    "cody": "Cody_(Chilean_player)",
    "curty": "Curty",
    "frosty": "Frosty_(José_Eduardo)",
    "zynts": "Zynts",
    "STEPZ": "STEPZ_(Eloy_Rodríguez)",
    "YoungJae": "YoungJae",
    "Xyno": "Xyno",
    "Keine": "Keine",
    "Trigger": "Trigger_(Kim_Eui-joo)",
    "Kuri": "Kuri",
    "Wizer": "Wizer",
    "Disamis": "Disamis",
    "Mireu": "Mireu",
    "Kaiwing": "Kaiwing",
    "Feisty": "Feisty",
    "Curse": "Curse",
    "Duduhh": "Duduhh",
    "Ackerman": "Ackerman_(Gabriel_Aparicio)",
    "Devost": "Devost",
    "Booki": "Booki",
    "Enga": "Enga",
    "Snaker": "Snaker",
    "Toplop": "TopLop",
    "Momochi": "Momochi",
    "Rabelo": "Rabelo",
    "Guigo": "Guigo",
    "Tutsz": "Tutsz",
    "Robo": "Robo",
    "CarioK": "CarioK",
    "RedBert": "RedBert",
    "Samkz": "Samkz",
    "uZent": "UZent",
    "sarolu": "Sarolu",
    "Morttheus": "Morttheus",
    "Drakehero": "Drakehero",
}

# Nicks do seed CBLOL 2026 (+ subs)
ALL_NICKS = [
    "zynts", "STEPZ", "Kaze", "Rabelo", "frosty",
    "Guigo", "Tatu", "Tutsz", "Ayu", "JoJo",
    "Wizer", "Disamis", "Mireu", "ceo", "Kaiwing",
    "Zest", "Curse", "Feisty", "Duduhh", "Ackerman",
    "curty", "Peach", "cody", "BAO", "Momochi",
    "Xyno", "YoungJae", "Envy", "Bull", "RedBert",
    "Robo", "CarioK", "Keine", "Trigger", "Kuri",
    "Devost", "Booki", "Enga", "Snaker", "Toplop",
    "Samkz", "uZent", "sarolu", "Morttheus", "Drakehero",
]

SKIP_RE = re.compile(
    r"(Square|logo|Logo|Disambig|std\.png|Wordmark|wordmark|Banner|icon)",
    re.I,
)
YEAR_RE = re.compile(r"(20\d{2})")


def api_get(params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    url = f"https://lol.fandom.com/api.php?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_images(page: str) -> list[str]:
    try:
        data = api_get({"action": "parse", "page": page, "prop": "images", "format": "json"})
    except urllib.error.HTTPError as e:
        print(f"  [http {e.code}] parse {page}")
        return []
    except Exception as e:
        print(f"  [err] parse {page}: {e}")
        return []
    parse = data.get("parse") or {}
    return list(parse.get("images") or [])


def score_image(name: str, nick: str) -> int:
    if SKIP_RE.search(name):
        return -1000
    nlow = name.lower()
    nick_l = nick.lower().replace("ø", "o")
    score = 0
    if nick_l in nlow:
        score += 50
    years = [int(y) for y in YEAR_RE.findall(name)]
    if years:
        score += max(years) - 2000  # prefer recent
    if "cblol" in nlow or "split" in nlow or "worlds" in nlow or "msi" in nlow:
        score += 10
    if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        score += 5
    return score


def pick_best_image(images: list[str], nick: str) -> str | None:
    ranked = sorted(
        ((score_image(img, nick), img) for img in images),
        key=lambda x: x[0],
        reverse=True,
    )
    for sc, img in ranked:
        if sc >= 50:  # must mention nick
            return img
    # fallback: any non-skipped with positive score
    for sc, img in ranked:
        if sc > 0:
            return img
    return None


def image_url(filename: str) -> str | None:
    try:
        data = api_get(
            {
                "action": "query",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            }
        )
    except Exception as e:
        print(f"  [err] imageinfo {filename}: {e}")
        return None
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if infos and infos[0].get("url"):
            return infos[0]["url"]
    return None


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = resp.read()
        if len(data) < 800:
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  [dl fail] {e}")
        return False


def slugify(nick: str) -> str:
    s = nick.strip().lower()
    s = s.replace("ø", "o").replace("Ø", "o")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "player"


def main() -> None:
    import sys

    only_missing = "--missing" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    meta: dict[str, dict] = {}

    # Carrega mapa anterior se existir
    if MAP_TS.exists():
        text = MAP_TS.read_text(encoding="utf-8")
        for m in re.finditer(r'"([^"]+)":\s*"([^"]+)"', text):
            mapping[m.group(1)] = m.group(2)

    nicks = ALL_NICKS
    if only_missing:
        nicks = [
            n
            for n in ALL_NICKS
            if not (mapping.get(n) or mapping.get(n.lower()))
            or not (ROOT / "frontend" / "public" / (mapping.get(n) or mapping.get(n.lower()) or "x").lstrip("/")).exists()
        ]
        print(f"Reprocessando {len(nicks)} nicks sem foto local…")

    for i, nick in enumerate(nicks):
        print(f"[{i+1}/{len(nicks)}] {nick}")
        page = PAGE_OVERRIDES.get(nick, nick)
        # Normalize special chars in page titles for URL
        time.sleep(1.1)
        images = list_images(page)
        if not images and page != nick:
            time.sleep(0.8)
            images = list_images(nick)
        # tenta search se vazio
        if not images:
            time.sleep(0.7)
            try:
                data = api_get(
                    {
                        "action": "query",
                        "list": "search",
                        "srsearch": nick,
                        "format": "json",
                        "srlimit": 3,
                    }
                )
                hits = (data.get("query") or {}).get("search") or []
                for hit in hits:
                    title = hit.get("title") or ""
                    if title and "Tournament" not in title:
                        time.sleep(0.8)
                        images = list_images(title)
                        if images:
                            page = title
                            break
            except Exception:
                pass
        best = pick_best_image(images, nick) if images else None
        if not best:
            print("  -> silhouette (sem foto adequada)")
            meta[nick] = {"status": "silhouette", "page": page}
            continue
        time.sleep(0.6)
        url = image_url(best)
        if not url:
            print(f"  -> no url for {best}")
            meta[nick] = {"status": "silhouette", "page": page, "file": best}
            continue
        slug = slugify(nick)
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        dest = OUT_DIR / f"{slug}{ext}"
        if download(url, dest):
            rel = f"/players/{slug}{ext}"
            mapping[nick] = rel
            mapping[nick.lower()] = rel
            print(f"  -> OK {rel} ({best})")
            meta[nick] = {"status": "photo", "page": page, "file": best, "url": url, "local": rel}
        else:
            print("  -> download failed, silhouette")
            meta[nick] = {"status": "silhouette", "page": page, "file": best, "url": url}

    META_JSON.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # TS map
    lines = [
        "/** Auto-gerado por scripts/fetch_player_photos.py — não editar à mão se for re-rodar o script. */",
        "/** Mapa nick (seed) -> caminho público da foto. Ausente = silhueta. */",
        "export const PLAYER_PHOTO_MAP: Record<string, string> = {",
    ]
    # unique by path, prefer original nick key
    seen_paths: set[str] = set()
    for nick, path in sorted(mapping.items(), key=lambda x: x[0].lower()):
        if nick != nick.lower() or nick.lower() not in {k.lower() for k in mapping if k != nick}:
            pass
        key = nick
        # only emit one canonical key per nick from ALL_NICKS
        if key not in ALL_NICKS and key not in {n.lower() for n in ALL_NICKS}:
            continue
        if path in seen_paths and key.islower():
            continue
        seen_paths.add(path)
        lines.append(f'  "{key}": "{path}",')
    # emit ALL_NICKS that have mapping
    lines = [
        "/** Auto-gerado por scripts/fetch_player_photos.py */",
        "/** Nick do seed -> /players/.... Ausente ou vazio = silhueta (sem foto de campeão). */",
        "export const PLAYER_PHOTO_MAP: Record<string, string> = {",
    ]
    for nick in ALL_NICKS:
        path = mapping.get(nick) or mapping.get(nick.lower())
        if path:
            lines.append(f'  {json.dumps(nick)}: {json.dumps(path)},')
    lines.append("};")
    lines.append("")
    lines.append("export function getPlayerPhotoUrl(name: string | undefined | null): string | null {")
    lines.append("  if (!name) return null;")
    lines.append("  const direct = PLAYER_PHOTO_MAP[name];")
    lines.append("  if (direct) return direct;")
    lines.append("  const lower = name.toLowerCase();")
    lines.append("  for (const [k, v] of Object.entries(PLAYER_PHOTO_MAP)) {")
    lines.append("    if (k.toLowerCase() === lower) return v;")
    lines.append("  }")
    lines.append("  return null;")
    lines.append("}")
    lines.append("")
    MAP_TS.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nFotos: {sum(1 for n in ALL_NICKS if mapping.get(n) or mapping.get(n.lower()))}/{len(ALL_NICKS)}")
    print(f"Mapa: {MAP_TS}")
    print(f"Arquivos: {OUT_DIR}")


if __name__ == "__main__":
    main()
