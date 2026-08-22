"""Nij Begun isolatieplan engine — PUBLIC API.

Exposes the stable contract the SaaS builds against.
Implementation: Renze's production engine (see docs/engine-package.md).

Golden rule: the engine NEVER computes the regulated NTA 8800 number.
The advisor's attested Vabi does. Here we only prepare Vabi's input and read its output.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, is_dataclass
from typing import Any


# Engine version — bump when dossier shape or calculation behaviour changes.
# Stored on every dossier + engine_run row for reproducibility/audit.
ENGINE_VERSION = "0.1.0"
DOSSIER_SCHEMA_VERSION = "0.3"

# Path to the official Nij Begun Word template (shipped as package data).
_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "isolatieplan_template.docx")


def _to_dossier(dossier: Any):
    """Convert a dict to a Dossier dataclass if needed."""
    if isinstance(dossier, dict):
        from core.dossier import Dossier
        return Dossier.from_dict(dossier)
    return dossier


def _to_dict(obj: Any) -> Any:
    """Convert a dataclass to a plain dict if needed."""
    return asdict(obj) if is_dataclass(obj) else obj


def _load_catalog() -> dict:
    """Load the bundled Nij Begun Maatregelencatalogus (the full dict; the engine
    indexes into catalog["maatregelen"] itself)."""
    import json
    import os as _os

    import catalog as _catalog_pkg

    path = _os.path.join(_os.path.dirname(_catalog_pkg.__file__), "catalog.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_dossier(plan_json: Any, report_pdf: Any = None, kozijnen: Any = None) -> tuple[dict, list[str]]:
    """MagicPlan export → (canonical dossier dict, list of gap descriptions).

    Args:
        plan_json: Parsed MagicPlan API plan JSON (dict).
        report_pdf: MagicPlan project-report PDF — path string or bytes.
        kozijnen: Optional pre-parsed kozijn data (from form push).

    Returns:
        (dossier, gaps) where gaps is a list of human-readable strings describing
        missing information the advisor must supply.
    """
    from magicplan import assemble, report_parser

    _tmp = None
    report_path = None
    if report_pdf is not None:
        if isinstance(report_pdf, (bytes, bytearray)):
            _tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            _tmp.write(report_pdf)
            _tmp.flush()
            report_path = _tmp.name
        else:
            report_path = str(report_pdf)

    try:
        report = report_parser.parse(report_path) if report_path else {}
        dos = assemble.build_dossier(report, kozijnen or {}, plan_json)
    finally:
        if _tmp:
            _tmp.close()
            os.unlink(_tmp.name)

    dossier_dict = _to_dict(dos)

    from validator.validate import validate as _validate
    # validate() returns (issues, dossier); issues = [(severity, message), ...]
    issue_list, _updated = _validate(dos)
    gaps = [f"[{sev}] {msg}" for sev, msg in (issue_list or [])]

    return dossier_dict, gaps


def generate_vabi_import(dossier: Any) -> dict:
    """Dossier → three importable Vabi EPA-W library XMLs + import instructions.

    Returns a dict with keys:
        constructies  – XML string (Constructiebibliotheek)
        objecten      – XML string (Objectenbibliotheek)
        installaties  – XML string (Installatiebibliotheek)
        instructions  – plain-text import instructions (ZELF DOEN list)
    """
    from vabi.generate_all import generate_all

    dos = _to_dossier(dossier)

    with tempfile.TemporaryDirectory() as outdir:
        result = generate_all(dos, outdir)
        output = {}
        for key in ("constructies", "objecten", "installaties"):
            path = result[key][0]
            with open(path, encoding="utf-8") as fh:
                output[key] = fh.read()
        with open(result["readme"], encoding="utf-8") as fh:
            output["instructions"] = fh.read()

    return output


def read_vabi_result(vabi_export: Any) -> dict:
    """Vabi export/monitoringbestand → key numbers + Nij Begun Standaard test.

    Args:
        vabi_export: Path to the EPA monitoring XML, or its contents as a string/bytes.

    Returns a dict with at least:
        energiebehoefte  – float (kWh/m2.jr) or None
        standaard        – float (kWh/m2.jr) or None
        voldoet          – bool or None
        labelklasse      – str or None
        raw              – full parsed dict
    """
    from vabi.result_reader import read_results

    if isinstance(vabi_export, (bytes, bytearray)):
        vabi_export = vabi_export.decode("utf-8", errors="replace")

    if isinstance(vabi_export, str) and not os.path.exists(vabi_export):
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w", encoding="utf-8") as fh:
            fh.write(vabi_export)
            tmp_path = fh.name
        try:
            raw = read_results(tmp_path)
        finally:
            os.unlink(tmp_path)
    else:
        raw = read_results(str(vabi_export))

    # result_reader.read_results() heeft de NettoWarmtebehoefte/IndicatorEnergiebehoefte-keuze al
    # gemaakt (_toetswaarde); hergebruik die i.p.v. de fallback-regel hier te dupliceren.
    eb = raw.get("_toetswaarde")
    st = raw.get("Standaard")
    return {
        "energiebehoefte": float(eb) if eb is not None else None,
        "standaard": float(st) if st is not None else None,
        "voldoet": (float(eb) <= float(st)) if (eb is not None and st is not None) else None,
        "labelklasse": raw.get("Labelklasse"),
        "raw": raw,
    }


def select_maatregelen(dossier: Any, results: dict | None = None) -> list[dict]:
    """Dossier + optional Vabi results → recommended measure set.

    Returns a list of maatregel dicts (each has at least 'code', 'omschrijving', 'kosten').
    """
    from engine.measure_engine import run as _run

    dos = _to_dossier(dossier)
    # measure_engine.run(dossier, catalog) mutates dossier.maatregelen and returns
    # (dossier, notes). It needs the catalogus passed in.
    dos, _notes = _run(dos, _load_catalog())
    return [_to_dict(m) for m in dos.maatregelen]


def render_isolatieplan(dossier: Any, template_path: str | None = None) -> dict:
    """Dossier → filled official Nij Begun Word template as bytes + JSON summary.

    Returns a dict with keys:
        docx  – bytes of the filled .docx
        pdf   – None (TODO: LibreOffice headless — see backlog P1)
        json  – dossier dict (echoed back for audit)
    """
    from isolatieplan.fill_template import fill

    dos = _to_dossier(dossier)
    tpl = template_path or _TEMPLATE_PATH

    with tempfile.TemporaryDirectory() as outdir:
        out_path = os.path.join(outdir, "isolatieplan.docx")
        fill(dos, tpl, out_path)
        with open(out_path, "rb") as fh:
            docx_bytes = fh.read()

    return {
        "docx": docx_bytes,
        "pdf": None,
        "json": _to_dict(dos),
    }


def validate(dossier: Any) -> dict:
    """KWACO 'sluitend' checklist — validate a dossier before Vabi generation.

    Returns a dict with keys:
        valid   – bool (True if no BLOKKEREND issues)
        issues  – list of {"severity": ..., "message": ...} dicts
    """
    from validator.validate import validate as _validate

    dos = _to_dossier(dossier)
    # validate() returns (issues, updated_dossier) where issues = [(severity, message), ...]
    issue_list, _updated = _validate(dos)

    issues = []
    blockers = 0
    for sev, msg in (issue_list or []):
        issues.append({"severity": sev, "message": msg})
        if sev == "BLOKKEREND":
            blockers += 1

    return {"valid": blockers == 0, "issues": issues}


__all__ = [
    "ENGINE_VERSION",
    "DOSSIER_SCHEMA_VERSION",
    "build_dossier",
    "generate_vabi_import",
    "read_vabi_result",
    "select_maatregelen",
    "render_isolatieplan",
    "validate",
]
