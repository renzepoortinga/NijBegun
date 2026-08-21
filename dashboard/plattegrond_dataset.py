"""Read-only inventarisatie van de werkelijk aanwezige taak-022-bronfixtures."""
from __future__ import annotations

import json
from pathlib import Path

from magicplan.statistics_csv import build_dossier
from vabi.monitor_xml import parse as parse_monitor


def inventariseer(root):
    root = Path(root)
    plan_pad = root / "tests" / "fixtures" / "magicplan_plan_voorbeeld.json"
    csv_pad = root / "tests" / "fixtures" / "statistics_voorbeeld.csv"
    monitor_pad = root / "tests" / "fixtures" / "monitor_voorbeeld.xml"
    with plan_pad.open(encoding="utf-8") as fh:
        plan = json.load(fh)
    plan_vloeren = [{"naam": str(v.get("name") or ""),
                     "ruimtes": [{"naam": str(r.get("name") or ""), "oppervlakte_m2": r.get("area")}
                                  for r in v.get("rooms") or []]}
                    for v in plan.get("floors") or []]
    csv_dossier, _csv_notes = build_dossier(str(csv_pad))
    monitor_dossier, _monitor_root = parse_monitor(str(monitor_pad))
    bronnen = [
        {"pad": str(plan_pad.relative_to(root)).replace("\\", "/"), "type": "magicplan_json",
         "vloeren": plan_vloeren, "heeft_raster": False},
        {"pad": str(csv_pad.relative_to(root)).replace("\\", "/"), "type": "magicplan_statistics_csv",
         "vloeren": [{"naam": v.naam, "ruimtes": [
             {"naam": r.naam, "oppervlakte_m2": r.oppervlakte_m2}
             for r in csv_dossier.geometrie.ruimtes if not r.verdieping or r.verdieping == v.naam]}
             for v in csv_dossier.geometrie.vloeren], "heeft_raster": False},
        {"pad": str(monitor_pad.relative_to(root)).replace("\\", "/"), "type": "vabi_monitor",
         "vloeren": [{"naam": v.naam, "ruimtes": [
             {"naam": r.naam, "oppervlakte_m2": r.oppervlakte_m2}
             for r in monitor_dossier.geometrie.ruimtes if not r.verdieping or r.verdieping == v.naam]}
             for v in monitor_dossier.geometrie.vloeren], "heeft_raster": False},
    ]
    return {"bronnen": bronnen, "aantal_vloeren": sum(len(b["vloeren"]) for b in bronnen),
            "aantal_rastervloeren": sum(len(b["vloeren"]) for b in bronnen if b["heeft_raster"])}
