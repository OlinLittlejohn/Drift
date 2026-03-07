#!/usr/bin/env python3
"""
Riffle — Fetch real OSM river geometry from Overpass API
Fetches each river individually with retries to avoid batch timeouts.

Usage:
  python3 fetch_geometry.py

Requirements:
  pip install requests
"""

import requests
import json
import time

RIVERS = [
    "Willamette River",
    "Deschutes River",
    "Sandy River",
    "Clackamas River",
    "Rogue River",
    "Umpqua River",
    "John Day River",
    "McKenzie River",
    "Owyhee River",
    "Illinois River",
    "Nehalem River",
    "Siletz River",
    "Coquille River",
    "Powder River",
    "Malheur River",
]

RIVER_CENTERS = {
    "Willamette River": (44.5,  -123.1),
    "Deschutes River":  (44.5,  -121.4),
    "Sandy River":      (45.4,  -122.1),
    "Clackamas River":  (45.2,  -122.4),
    "Rogue River":      (42.4,  -123.3),
    "Umpqua River":     (43.1,  -123.65),
    "John Day River":   (44.75, -120.20),
    "McKenzie River":   (44.13, -122.47),
    "Owyhee River":     (43.07, -117.17),
    "Illinois River":   (42.31, -123.32),
    "Nehalem River":    (45.68, -123.60),
    "Siletz River":     (44.85, -123.70),
    "Coquille River":   (43.18, -124.00),
    "Powder River":     (44.80, -117.80),
    "Malheur River":    (43.98, -117.70),
}

BBOX = "41.9,-124.7,46.3,-116.4"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def fetch_one(river_name, retries=4):
    """Fetch a single river with retry on failure."""
    query = (
        f'[out:json][timeout:60];'
        f'way["waterway"="river"]["name"="{river_name}"]({BBOX});'
        f'out geom;'
    )
    for attempt in range(retries):
        try:
            r = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
            if r.status_code == 429:
                wait = 45 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 504:
                wait = 20 * (attempt + 1)
                print(f"    Gateway timeout, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["elements"]
        except requests.exceptions.Timeout:
            wait = 20 * (attempt + 1)
            print(f"    Request timeout, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(15)
            else:
                raise
    raise Exception(f"Failed after {retries} attempts")


def elements_to_segments(elements, river_name):
    segments = []
    for el in elements:
        if not el.get("geometry"):
            continue
        if el.get("tags", {}).get("name") != river_name:
            continue
        coords = [[round(p["lat"], 5), round(p["lon"], 5)] for p in el["geometry"]]
        if len(coords) >= 2:
            segments.append(coords)
    return segments


def main():
    by_name = {}

    print("=== Fetching rivers one at a time ===\n")
    for i, name in enumerate(RIVERS):
        print(f"[{i+1}/{len(RIVERS)}] {name}...", flush=True)
        try:
            elements = fetch_one(name)
            segs = elements_to_segments(elements, name)
            if segs:
                by_name[name] = segs
                pts = sum(len(s) for s in segs)
                print(f"  OK: {len(segs)} segments, {pts} points")
            else:
                print(f"  No segments found — baked fallback will be used")
        except Exception as e:
            print(f"  FAILED: {e} — baked fallback will be used")

        # Polite delay between requests (skip after last one)
        if i < len(RIVERS) - 1:
            time.sleep(6)

    # Summary
    print(f"\n=== Results ===")
    got, missing = 0, 0
    for name in RIVERS:
        segs = by_name.get(name, [])
        pts = sum(len(s) for s in segs)
        if segs:
            print(f"  {name}: {len(segs)} segments, {pts} points")
            got += 1
        else:
            print(f"  {name}: MISSING — baked fallback will be used")
            missing += 1
    print(f"\n{got}/15 rivers fetched from OSM, {missing} using baked fallback")

    if not by_name:
        print("\nERROR: No rivers fetched. Check your internet connection.")
        return

    # Write output — only include rivers that were successfully fetched
    geometry = {name: {"segments": by_name[name]} for name in RIVERS if name in by_name}
    js_output = "const RIVER_GEOMETRY = " + json.dumps(geometry, separators=(",", ":")) + ";"

    with open("RIVER_GEOMETRY.js", "w") as f:
        f.write(js_output)

    print("\nWritten to RIVER_GEOMETRY.js")
    print("\nInstructions:")
    print("  1. Open RIVER_GEOMETRY.js")
    print("  2. Copy the entire line")
    print("  3. In index.html, find the line starting with:")
    print("       const RIVER_GEOMETRY = {")
    print("  4. Select and replace that entire line with the copied content")
    print("  5. Save and push to GitHub")
    print("\nNote: Any MISSING rivers above will continue using the existing")
    print("baked coordinates already in index.html — just leave those as-is.")


if __name__ == "__main__":
    main()