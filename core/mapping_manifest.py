"""
Mappingmanifest (taak 015): ÉÉN machineleesbare bron per ondersteunde MagicPlan-dropdown, die
bronlabel/opties, canoniek dossierveld, webapp-opties en VABI-pad/codes aan elkaar knoopt.

Waarom dit bestaat: dropdown-vocabulaire werd tot nu toe op minstens drie plekken apart onderhouden
(de parser-normalisatie in `magicplan/statistics_csv.py`, de `<select>`-opties in `dashboard/app.py`,
en de VABI-codes in `vabi/objecten_generate.py`/`vabi/installatie_generate.py`/`vabi/codebook.py`) —
met alleen een handmatig commentaar ("MOET gelijk blijven aan ...") als bewaking. Die drie liepen
al minstens één keer echt uit de pas (kozijnmateriaal-haakjes, mappingmanifest-audit 21-8-2026: de
parser produceerde "Metaal thermisch onderbroken" zonder haakjes, de webapp-`<select>` had alleen
"Metaal (thermisch onderbroken)" mét haakjes — bij een CSV-import werd de kozijnwaarde bij de
eerstvolgende webapp-save stil overschreven met de default; gefixt in dezelfde sessie als dit
manifest).

ELKE entry verwijst naar de ECHTE objecten in de code (`module:attribuut`) i.p.v. de opties hier
te dupliceren — zo kan dit manifest zelf nooit los raken van de code die het beschrijft.
`scripts/check_mapping_manifest.py` valideert elke referentie en signaleert drift; zie dat bestand
voor de uitleg per controle. `docs/mapping-overview.md` wordt UIT dit manifest gegenereerd
(`python scripts/check_mapping_manifest.py --write-doc`), nooit andersom.

Velden:
  id             korte sleutel voor deze mapping
  bronform       MagicPlan-form/veldgroep waarin het label staat (zie docs/magicplan-forms-live.md)
  bronlabel      het letterlijke MagicPlan-veldlabel (of labels, als meerdere velden dezelfde
                 canonieke opties delen, bv. de 4 begrenzing-velden)
  verplicht      "verplicht" | "optioneel" | "conditioneel: <voorwaarde>"
  canoniek_veld  dossierpad (SchilDeel/Opname/... attribuut) waar de canonieke waarde landt
  parser_canon   "module:attribuut" van de dict/functie die MagicPlan-labels normaliseert naar de
                 canonieke waarde, of None als de parser de MagicPlan-waarde ongewijzigd doorzet
  webapp_opties  "module:attribuut" van de `<select>`-optielijst in de webapp-editor, of None als
                 er geen losse webapp-dropdown voor dit veld bestaat
  vabi_pad       mensleesbaar VABI-bibliotheekpad (bib > element > XML-veld)
  vabi_codes     "module:attribuut" van de code-dict, "vabi.codebook:<methode>" voor codebook-
                 afgeleide velden (zelfvaliderend uit een echte export), of None als er nog geen
                 vaste code-tabel is (dan blijft de sjabloonwaarde staan + wordt geflagd — golden rule)
  bewijsstatus   "bevestigd" (live in EPA geverifieerd, zie bron_doc) | "gedeeltelijk" (een deel van
                 de codes bevestigd) | "geflagd" (nog niet in EPA bevestigd; tool gokt nooit, meldt
                 luid in plaats van te schrijven)
  bron_doc       waar de bevestiging vandaan komt (mens-leesbare voetnoot)
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VeldMapping:
    id: str
    bronform: str
    bronlabel: str
    verplicht: str
    canoniek_veld: str
    parser_canon: Optional[str]
    webapp_opties: Optional[str]
    vabi_pad: str
    vabi_codes: Optional[str]
    bewijsstatus: str
    bron_doc: str
    # Voor Codebook-afgeleide velden (vabi_codes="vabi.codebook:Codebook.<methode>") normaliseert de
    # generator de dossierwaarde EERST via een eigen functie (bv. 'HR (dubbel glas met coating)' ->
    # 'hr' vóór 'dubbel' checken, vacuümglas -> hr++) — die zit in vabi/constructie_generate.py, niet
    # in het codebook zelf. Referentie hier zodat de drift-check dezelfde weg bewandelt als de echte
    # generator i.p.v. de rauwe webapp-optie tegen het codebook te gooien.
    vabi_codes_normalizer: Optional[str] = None
    # Webapp-opties die BEWUST geen VABI-code opleveren (golden rule: de generator flagt deze i.p.v.
    # te gokken, zie bron_doc) — geen drift, geen fout.
    vabi_onbevestigde_opties: List[str] = field(default_factory=list)


MANIFEST: List[VeldMapping] = [
    VeldMapping(
        id="begrenzing",
        bronform="Constructies (project) + Gevel per wand / Vloer per kamer / Deur (element)",
        bronlabel="Gevel - begrenzing · Vloer - begrenzing · Begrenzing (anders dan buitenlucht)",
        verplicht="conditioneel: alleen tonen als niet Buitenlucht",
        canoniek_veld="SchilDeel.begrenzing",
        parser_canon="magicplan.statistics_csv:_BEGR_CANON",
        webapp_opties="dashboard.app:BEGR_OPTS",
        vabi_pad="Objecten > Hoofdvlak > GrenstAan",
        # Functie i.p.v. de rauwe GRENST_AAN_CODE-dict: AOR/AOS/Sterk geventileerd/AVR lopen in de
        # BASISOPNAME via een aparte tak (tellen als buitenlucht, zie _DETAIL_CODE/_AVR in dezelfde
        # module) -- de functie is de echte, volledige vertaalweg die de generator ook gebruikt.
        vabi_codes="vabi.objecten_generate:_grenst_aan_code",
        bewijsstatus="bevestigd",
        bron_doc="vabi/refs/grenstaan_mapping.md; volledige dropdown 0-9 live afgelezen EPA 12.0.1 (19-7-2026)",
    ),
    VeldMapping(
        id="glastype",
        bronform="Raam/paneel + Deur (element)",
        bronlabel="Type glas · Type glas (indien glas in deur) · Bovenlicht deur - type glas",
        verplicht="verplicht (hoofdraam) / conditioneel (bovenlicht/deur)",
        canoniek_veld="SchilDeel.glastype",
        parser_canon="magicplan.statistics_csv:_GLAS_CANON",
        webapp_opties="dashboard.app:GLAS_OPTS",
        vabi_pad="Constructiebibliotheek > Constructie(Raam) > Glas (via vabi.codebook.Codebook.glas_code)",
        vabi_codes="vabi.codebook:Codebook.glas_code",
        vabi_codes_normalizer="vabi.constructie_generate:_norm_glas",
        vabi_onbevestigde_opties=["Onbekend"],
        bewijsstatus="bevestigd",
        bron_doc="vabi/codebook.py leidt de codes zelf af uit vabi/refs/standaard_constructies_v120001001.xml (219 constructies); "
                 "'Onbekend' wordt bewust NIET gegokt (generator-issue, audit-glas-F3 15-7)",
    ),
    VeldMapping(
        id="kozijnmateriaal",
        bronform="Raam/paneel + Deur (element)",
        bronlabel="Kozijnmateriaal",
        verplicht="optioneel (default Hout of kunststof)",
        canoniek_veld="SchilDeel.kozijnmateriaal",
        parser_canon="magicplan.statistics_csv:_KOZIJN_MAT",
        webapp_opties="dashboard.app:KOZ_OPTS",
        vabi_pad="Constructiebibliotheek > Constructie(Raam/Deur) > Kozijn (via vabi.codebook.Codebook.kozijn_code)",
        vabi_codes="vabi.codebook:Codebook.kozijn_code",
        vabi_codes_normalizer="vabi.constructie_generate:_norm_kozijn",
        bewijsstatus="bevestigd",
        bron_doc="vabi/codebook.py (zelfde export als glastype); labels incl. haakjes = NTA 8.3 kozijntype A/B/C, letterlijk het live MagicPlan-optielabel (docs/magicplan-forms-live.md)",
    ),
    VeldMapping(
        id="gevel_orientatie",
        bronform="Object (project) + Gevel per wand (override)",
        bronlabel="Oriëntatie voorgevel · Gevel - oriëntatie (override)",
        verplicht="verplicht (voorgevel)",
        canoniek_veld="SchilDeel.orientatie",
        parser_canon=None,   # de parser leidt overige gevels af (_orient_afleiden), zet zelf al de canonieke kompas-string
        webapp_opties="dashboard.app:ORI_OPTS",
        vabi_pad="Objecten > Hoofdvlak > Orientatie (Geometrie-tabblad)",
        vabi_codes="vabi.objecten_generate:ORIENTATIE_CODE",
        vabi_onbevestigde_opties=[""],   # lege keuze (nog niet ingevuld) -> geen code, geen drift
        bewijsstatus="bevestigd",
        bron_doc="Geometrie-export voorbeeldproject 'hoekwoning' (18-7-2026): Zuid=0/Noord=4/Oost=6 rechtstreeks bevestigd, rest via dropdownvolgorde",
    ),
    VeldMapping(
        id="woningtype_subtype",
        bronform="Object (project)",
        bronlabel="Woningtype",
        verplicht="verplicht",
        canoniek_veld="Identificatie.woningtype",
        parser_canon=None,
        webapp_opties="dashboard.app:WONINGTYPE_OPTS",
        vabi_pad="Objecten > Object > Subtype (woningpositie; Gebouwtype vast 0=Eengezinswoning, Nij Begun-scope)",
        vabi_codes="vabi.objecten_generate:_subtype_code",
        vabi_onbevestigde_opties=["Galerijwoning", "Portiekwoning", "Maisonnette (bovenwoning)",
                                  "Woning boven bedrijfsruimte"],
        bewijsstatus="gedeeltelijk",
        bron_doc="Objecten-export hoekwoning (Subtype=1) + monitor-fixture tussenwoning (Subtype=2), 18-7-2026; "
                 "de 4 meergezins-varianten vallen buiten de Nij Begun-scope (grondgebonden eengezinswoningen) "
                 "en worden bewust NIET gegokt (golden rule)",
    ),
    VeldMapping(
        id="pv_orientatie",
        bronform="Installaties > ZONNE-ENERGIE (project)",
        bronlabel="PV - oriëntatie",
        verplicht="conditioneel: alleen als PV aanwezig",
        canoniek_veld="ZonneEnergieSysteem.orientatie",
        parser_canon=None,
        webapp_opties=None,
        vabi_pad="Installatiebibliotheek > ZonneEnergie > Orientatie (LET OP: eigen enum, 0=N startend, ANDERS dan de geometrie-Orientatie)",
        vabi_codes="vabi.installatie_generate:PV_ORIENTATIE",
        bewijsstatus="bevestigd",
        bron_doc="PV end-to-end geverifieerd (22-6-2026): 12x1,70=20,40 m2 PV/Zuid/35 graden foutloos geimporteerd in EPA",
    ),
]


def get(id_):
    for m in MANIFEST:
        if m.id == id_:
            return m
    raise KeyError("Geen mapping-manifestentry met id=%r" % id_)


def resolve(ref):
    """'module.pad:attribuut' -> het echte Python-object (dict/functie/lijst). Faalt luid (ImportError/
    AttributeError) als de code-referentie niet meer klopt -- dat IS de drift-detectie."""
    if ref is None:
        return None
    mod_naam, _, attr_pad = ref.partition(":")
    if not attr_pad:
        raise ValueError("Ongeldige manifest-referentie %r (verwacht 'module:attribuut')" % ref)
    import importlib
    obj = importlib.import_module(mod_naam)
    for deel in attr_pad.split("."):
        obj = getattr(obj, deel)
    return obj
