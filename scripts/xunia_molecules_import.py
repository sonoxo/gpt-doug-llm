#!/usr/bin/env python3
"""Import a bounded set of public PubChem compounds into XUNIA CL1 Molecules.

No API key, no external runtime browser API, no paid services.
Explicit CID-only import, bounded per run, minimal rate, atomic write.
2D coordinates are illustrative in the 3D viewer; NOT physical 3D conformers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "molecules" / "catalogs" / "pubchem.json"
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
SCHEMA = "xunia.cl1.molecules.v1"
PERIODIC = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr "
            "Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd "
            "Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho "
            "Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra "
            "Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs "
            "Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()
ORDER_MAP = {1: 1, 2: 2, 3: 3}


def fetch_json(url: str) -> dict:
    """One bounded public API request; HTTP 429 retry only twice."""
    if not url.startswith(BASE):
        raise ValueError("Refusing a non-PubChem API address")
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "XUNIA-CL1-Molecular-Atlas/1.0 (public educational importer)",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=18) as response:
                raw = response.read(5_000_001)
            if len(raw) > 5_000_000:
                raise ValueError("PubChem response exceeds maximum size")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("PubChem returned an unexpected data type")
            return value
        except HTTPError as exc:
            if exc.code not in (429, 503) or attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
        except URLError:
            raise
    raise RuntimeError("PubChem endpoint unavailable")


def parse_cid(cid: int, properties: dict, structural: dict) -> dict:
    record = structural["PC_Compounds"][0]
    info = properties["PropertyTable"]["Properties"][0]
    if int(info["CID"]) != cid:
        raise ValueError("CID mismatch in PubChem response")
    atomic_numbers = record["atoms"]["element"]
    aids = record["atoms"]["aid"]
    if len(aids) > 350 or len(aids) != len(atomic_numbers):
        raise ValueError("Compound exceeds the safe atom bound")
    if not aids or len(set(aids)) != len(aids):
        raise ValueError("Missing or duplicate atom identifiers")
    coords = {}
    for record_coords in record.get("coords", []):
        if not record_coords.get("conformers"):
            continue
        conf = record_coords["conformers"][0]
        coord_aids = record_coords.get("aid", aids)
        xx, yy = conf.get("x", []), conf.get("y", [])
        if len(xx) == len(yy) == len(coord_aids):
            # Preserve the 2D chemical drawing. Do not infer physical conformers.
            coords = {
                aid: (float(xx[i]), float(yy[i]), 0.0)
                for i, aid in enumerate(coord_aids)
            }
            break
    atoms = []
    for ix, (aid, number) in enumerate(zip(aids, atomic_numbers)):
        number = int(number)
        if not 1 <= number <= len(PERIODIC):
            raise ValueError("Unsupported element number")
        x, y, z = coords.get(
            aid,
            (float(ix % 16) - 8, float(ix // 16) - 3, 0.0),
        )
        if max(abs(x), abs(y), abs(z)) > 200:
            raise ValueError("Coordinates out of bound")
        atoms.append({
            "id": int(aid),
            "element": PERIODIC[number - 1],
            "x": round(x, 4),
            "y": round(y, 4),
            "z": 0.0,
            "charge": 0,
        })
    bonds_data = record.get("bonds", {})
    b1, b2, orders = (
        bonds_data.get("aid1", []),
        bonds_data.get("aid2", []),
        bonds_data.get("order", []),
    )
    if len(b1) != len(b2) or len(b1) != len(orders) or len(b1) > 600:
        raise ValueError("Invalid PubChem bond list")
    all_aids = set(aids)
    bonds = []
    for a, b, order in zip(b1, b2, orders):
        if a not in all_aids or b not in all_aids or a == b:
            raise ValueError("Dangling PubChem bond")
        order = int(order)
        if order not in ORDER_MAP:
            # PubChem may encode aromatic or other bond types beyond 1/2/3.
            # Fail closed instead of silently inventing a bond order.
            raise ValueError("Unsupported bond order, CID %s" % cid)
        bonds.append({"a": int(a), "b": int(b), "order": ORDER_MAP[order]})
    mass = float(info["MolecularWeight"])
    if not 0 < mass < 100_000:
        raise ValueError("Molecular weight outside supported range")
    formula = str(info["MolecularFormula"])[:80]
    if not formula or not re.fullmatch(r"[A-Za-z0-9+()\[\]·.\-]+", formula):
        raise ValueError("Unsupported formula")
    name = str(info.get("IUPACName") or ("PubChem CID " + str(cid)))[:150]
    return {
        "id": "pubchem-" + str(cid),
        "name": name,
        "formula": formula,
        "domain": "imported",
        "status": "chemistry-reference",
        "astro_claim": "PubChem chemical structure only. No astronomical observation or detection claim.",
        "description": "PubChem CID %s: reference 2D connectivity imported from the public compound record. Hydrogens may be implicit." % cid,
        "atoms": atoms,
        "bonds": bonds,
        "molar_mass_gmol": round(mass, 4),
        "geometry": "pubchem-2d-coordinates-rotated-for-display-not-a-physical-3d-conformer",
        "source": "pubchem",
        "cid": cid,
        "source_label": "PubChem CID %d" % cid,
        "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/" + str(cid),
    }


def run(cids: list[int], maximum: int, dry_run: bool = False) -> int:
    unique = list(dict.fromkeys(cids))
    if not unique or len(unique) > maximum or len(unique) > 25:
        raise ValueError("Specify 1 to 25 CIDs within --limit")
    if any(cid < 1 or cid > 999_999_999 for cid in unique):
        raise ValueError("CID must be a positive PubChem compound identifier")
    existing = json.loads(OUT.read_text(encoding="utf-8"))
    if existing["schema"] != SCHEMA or not isinstance(existing.get("molecules"), list):
        raise ValueError("Invalid existing catalog")
    records = {item["id"]: item for item in existing["molecules"]}
    for i, cid in enumerate(unique):
        print("PubChem CID %d (%d/%d)" % (cid, i + 1, len(unique)), flush=True)
        props = fetch_json(
            BASE + "%d/property/MolecularFormula,MolecularWeight,IUPACName/JSON" % cid
        )
        time.sleep(0.6)
        structure = fetch_json(BASE + "%d/JSON?record_type=2d" % cid)
        mol = parse_cid(cid, props, structure)
        records[mol["id"]] = mol
        print("  %s / %s / %d displayed atoms" %
              (mol["name"], mol["formula"], len(mol["atoms"])), flush=True)
        if i < len(unique) - 1:
            time.sleep(0.6)
    if len(records) > 500:
        raise ValueError("Local import exceeds 500 molecules; split into a separate catalog")
    payload = {
        "schema": SCHEMA,
        "status": "imported",
        "updated": date.today().isoformat(),
        "provenance": "PubChem public PUG REST property and 2D compound records, fetched by explicit CID.",
        "molecules": list(records.values()),
    }
    if dry_run:
        print(json.dumps({"would_write": str(OUT), "total": len(records)}, indent=2))
        return 0
    output = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    fd, temporary = tempfile.mkstemp(dir=OUT.parent, prefix=".pubchem-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(output)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, OUT)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    print("Saved %d source-backed compounds to %s" % (len(records), OUT))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bounded, free PubChem compound import for XUNIA CL1 Molecules."
    )
    parser.add_argument("--cid", type=int, action="append", required=True,
                        help="PubChem compound identifier, repeat per compound")
    parser.add_argument("--limit", type=int, default=10,
                        help="Maximum compounds in this run (1–25); default 10")
    parser.add_argument("--dry-run", action="store_true",
                        help="Retrieve and validate without writing")
    args = parser.parse_args()
    if not 1 <= args.limit <= 25:
        parser.error("--limit must be between 1 and 25")
    try:
        return run(args.cid, args.limit, args.dry_run)
    except (ValueError, KeyError, IndexError, TypeError, HTTPError,
            URLError, TimeoutError, json.JSONDecodeError) as exc:
        print("XUNIA MOLECULE IMPORT FAILED: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
