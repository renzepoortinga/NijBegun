"""
Canoniek dossier-datamodel = single source of truth voor de hele pijplijn.
Alle bouwstenen (MagicPlan-extractor, VABI-brug, isolatieplan-generator, validator)
lezen/schrijven dit model. JSON (de)serialiseerbaar.

Run direct om sample_dossier.json + canonical_schema.json te (her)genereren:
    python3 core/dossier.py
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict, fields, is_dataclass
from typing import List, Optional, Any
import json, os, datetime

SCHEMA_VERSION = "0.3"

# ---------- deelobjecten ----------
@dataclass
class Identificatie:
    bag_vboid: str = ""
    straat: str = ""
    huisnummer: str = ""
    postcode: str = ""
    plaats: str = ""
    bouwjaar: Optional[int] = None
    renovatiejaar: Optional[int] = None
    renovatiejaar_toelichting: str = ""
    woningtype: str = ""          # Vrijstaand | Twee-onder-een-kap | Hoekwoning | Tussenwoning | Meergezins | Repeterend
    type_dak: str = ""            # Hellend/Zadeldak/Lessenaar | Gedeeltelijk plat | Plat (VABI Daktype 0/1/2)
    aantal_bouwlagen: Optional[int] = None
    orientatie_voorgevel: str = ""  # kompas N..NW van de VOORGEVEL; de tool leidt achter/links/rechts hieruit af
                                    # (rechter = -90, linker = +90, achter = +180; 'vanaf de straat'-conventie)

@dataclass
class Adviseur:
    naam: str = ""
    bedrijf: str = ""
    telefoon: str = ""
    email: str = ""
    registratie: str = ""         # persoonsgebonden registratie/sleutel (tool-eis 4c)

@dataclass
class Opname:
    opnamedatum: str = ""         # YYYY-MM-DD
    rapportagedatum: str = ""
    type_advies: str = "Basis"    # Basis | Uitgebreid | Label
    qv10_gemeten: bool = False
    qv10_waarde: Optional[float] = None
    bewijslast: str = "Geen"      # Geen | Facturen | Tekeningen | Beide
    gevelhoogte_m: Optional[float] = None          # hoogte GEVEL (vloer tot dakvoet/goot); voor hart-op-hart-toeslag (ISSO 8.2)
    gebouwhoogte_m: Optional[float] = None         # hoogte GEBOUW (tot de nok); VABI Gebouwhoogte. UITSLUITEND
                                                   # handmatige invoer: leeg -> generator schrijft 0 + LUIDE flag
                                                   # (bewust GEEN berekende fallback; zie geen-aannames-beleid)
    gevel_tot_hartmaat_gemeten: bool = False       # True = gevel al tot hartmaat gemeten. De tool telt de
                                                   # hart-op-hart-toeslag NIET automatisch mee (besluit 19-7):
                                                   # hij geeft er een melding voor, jij zet 'm zelf in VABI
    thermische_massa_wanden: str = ""              # Licht | Zwaar | Zeer zwaar (EPA Rekenzone>Algemeen, geen "Half zwaar")
    thermische_massa_vloeren: str = ""             # Licht | Zwaar | Zeer zwaar (kan afwijken van de wanden)
    # --- Huidige woningstaat (isolatieplan sectie 3, V1-V6) die NIET uit de geometrie volgt ---
    gevel_isolatie_zijde: str = ""     # V1: Spouw | Binnenzijde | Buitenzijde | Geen | Onbekend
    dak_isolatie_zijde: str = ""       # V4: Binnenzijde | Buitenzijde | Onbekend (hellend én plat dak)
    bodemisolatie: str = ""            # V3: Ja | Nee | Onbekend (kruipruimte-bodemisolatie)
    kierdichting: str = ""             # V6: omschrijving/klasse van de huidige kierdichting

@dataclass
class VloerInfo:
    naam: str = ""
    oppervlakte_m2: float = 0.0
    hoogte_m: Optional[float] = None

@dataclass
class Ruimte:
    naam: str = ""
    functie: str = ""        # verblijfsruimte | keuken | badkamer | toilet | wasruimte | verkeer | overig
    oppervlakte_m2: float = 0.0

@dataclass
class Geometrie:
    gebruiksoppervlakte_ag_m2: float = 0.0
    verwarmd_volume_m3: Optional[float] = None
    perimeter_m: Optional[float] = None
    vloeren: List[VloerInfo] = field(default_factory=list)
    ruimtes: List[Ruimte] = field(default_factory=list)

@dataclass
class SchilDeel:
    id: str = ""
    type: str = ""                # gevel | vloer | dak | kozijn
    subtype: str = ""             # bv. Spouwmuur, Begane grondvloer, Hellend dak, Raam
    begrenzing: str = ""          # Buitenlucht | AOR | Grond | Aangrenzende woning
    orientatie: str = ""          # N..NW | (horizontaal)
    gevel_naam: str = ""          # voorgevel | achtergevel | linkergevel | rechtergevel (uit de wandnaam;
                                  #   de oriëntatie wordt hieruit + orientatie_voorgevel afgeleid)
    oppervlakte_m2: float = 0.0
    isolatie_aanwezig: str = "Onbekend"   # Ja | Nee | Onbekend (oud: Wel/Niet/Gedeeltelijk - beide ondersteund)
    rc_huidig: Optional[float] = None
    u_huidig: Optional[float] = None
    spouw_aanwezig: Optional[bool] = None
    spouwdikte_mm: Optional[float] = None          # breedte van de spouw (relevant voor Nij Begun: na-isolatie)
    perimeter_m: Optional[float] = None            # omtrek (vloer/gevel) — VEREIST voor VABI (randverliezen); auto uit MagicPlan of handmatig
    isolatiedikte_mm: Optional[float] = None
    glastype: str = ""            # Enkel | Dubbel | HR | HR+ | HR++ | Triple | ...
    kozijnmateriaal: str = ""     # Hout | Kunststof | Metaal | MTO | Aluminium
    rc_bron: str = ""             # Opgemeten dikte | Dikte onbekend | Kwaliteitsverklaring | Forfaitair (bouwjaar/renovatiejaar)
    bouwjaarklasse: str = ""      # per-bouwdeel klasse voor het beslisschema (bv. "Van 1975 t/m 1982"); wint van project-bouwjaar
    hellingshoek: Optional[float] = None          # dak: graden (bepaalt het schuine dakoppervlak)
    oppervlak_handmatig: Optional[float] = None   # dak: handmatig gemeten m2 (override op de berekening)
    rekenzone: int = 1                             # rekenzone-nummer (default 1; >1 bij meerdere zones)
    deur_met_raam_glas65: bool = False             # deur met raam >=65% glas -> telt als raam in VABI
    toevoerrooster: str = ""                       # ventilatie-toevoer via raam: Zelfregelend (ZR)|Niet-zelfregelend|Geen
    opmerkingen: str = ""

@dataclass
class Ventilatie:
    systeem: str = ""             # A | B | C | D | E (Gecombineerd) (+ toelichting)
    systeem_soort: str = ""       # Individueel | Collectief
    merk: str = ""
    type: str = ""
    installatiejaar: Optional[int] = None
    wtw_rendement_pct: Optional[float] = None
    co2_sturing: Optional[bool] = None
    zelfregelend: Optional[bool] = None       # vraaggestuurde/luchtdrukgestuurde roosters -> VABI Delta-p subsysteem
    tijdsturing: Optional[bool] = None         # -> VABI C3
    passieve_koeling: Optional[bool] = None
    kwaliteitsverklaring: Optional[bool] = None  # VLA; BCRG-opzoeking blijft handmatig in VABI
    subsysteem_code: str = ""     # optioneel: A1 | C2a | C4b ... (indien bekend)
    rekenzone: int = 1            # tot welke rekenzone deze installatie behoort (1..3)
    opmerkingen: str = ""

# ---------- installaties (gespiegeld aan VABI EPA 12) ----------
@dataclass
class Verwarming:
    systeem: str = ""             # Individueel | Gemeenschappelijk/collectief | Warmtelevering derden ...
    aantal_opwekkers: int = 1
    merk: str = ""
    type: str = ""
    installatiejaar: Optional[int] = None
    type_opwekker: str = ""       # Gasgestookte ketel | Warmtepomp elektrisch | WKK | Biomassaketel | ...
    subtype: str = ""             # HR107 | HR104 | VR | CR | lucht-water | ...
    direct_luchtverwarming: Optional[bool] = None
    opstelplaats: str = ""        # Binnen thermische zone | Buiten thermische zone | Onbekend
    kwaliteitsverklaring: Optional[bool] = None
    distributiemedium: str = ""   # Water | Lucht
    aanvoertemperatuur: str = ""  # 90/70 | 70/55 | 55/45 | 45/35 (LT = warmtepomp-indicator)
    type_distributie: str = ""    # Tweepijpssysteem | Eenpijpssysteem
    leidingen_onverwarmd: Optional[bool] = None
    afgifte: str = ""             # Radiatoren/convectoren | Vloer-/wandverwarming | Luchtverwarming | Combinatie
    regeling: str = ""
    rekenzone: int = 1            # tot welke rekenzone deze opwekker behoort (1..3)

@dataclass
class Tapwater:
    aantal_systemen: int = 1
    type_installatie: str = ""    # Individueel | Gemeenschappelijk/collectief | Warmtelevering derden ...
    aangesloten_op: str = ""      # Hele woning | Badkamer | Keuken
    type_opwekker: str = ""       # Compleet toestel | Gekoppeld aan cv (combi) | Aparte opwekker
    merk: str = ""
    type: str = ""
    installatiejaar: Optional[int] = None
    type_toestel: str = ""        # Gasgestookt combitoestel | Elektrische boiler | Warmtepompboiler | ...
    gaskeur: str = ""             # Met Gaskeur HR en CW | Met Gaskeur HR | Zonder Gaskeur | N.v.t.
    cw_klasse: str = ""           # CW1 | CW2 | CW3 | CW-4/5/6 | Onbekend
    open_verbranding: Optional[bool] = None
    kwaliteitsverklaring: Optional[bool] = None
    dwtw_aanwezig: Optional[bool] = None
    lengte_keuken: str = ""       # uittapleiding-lengteklasse
    lengte_badkamer: str = ""
    circulatieleiding: Optional[bool] = None
    rekenzone: int = 1            # tot welke rekenzone dit tapwatertoestel behoort (1..3)

@dataclass
class Koeling:
    aanwezig: bool = False
    systeem: str = ""             # Individueel | Gemeenschappelijk/collectief
    aantal_opwekkers: int = 1
    type_opwekker: str = ""       # Compressiekoeling | Absorptiekoeling | Vrije koeling
    expansie: str = ""            # Directe expansie in de ruimte (airconditioning) | Indirecte expansie
    splitsysteem: str = ""        # Single split | Multi split | VRF
    afgifte: str = ""             # Ventilatorconvectoren (aan buitenmuur) | Vloer-/wandkoeling | ...
    aantal_toestellen: Optional[int] = None
    kwaliteitsverklaring: Optional[bool] = None
    rekenzone: int = 1            # tot welke rekenzone dit koeltoestel behoort (1..3)

@dataclass
class ZonneEnergieSysteem:
    systeem: str = ""             # PV-panelen | PVT-panelen | Zonneboiler | Opslag
    merk: str = ""
    type: str = ""
    installatiejaar: Optional[int] = None
    aantal: Optional[int] = None
    oppervlak_per_paneel_m2: Optional[float] = None
    orientatie: str = ""          # N..NW | Oost-west | Plat
    hellingshoek: Optional[float] = None
    pv_type: str = ""             # Monokristallijn | Polykristallijn | Dunne film | Onbekend
    fabricagejaar: str = ""       # Voor 2018 | Vanaf 2018
    bouwintegratie: str = ""      # Goed/Matig geventileerd | Niet geventileerd (geïntegreerd)
    belemmering: Optional[bool] = None
    kwaliteitsverklaring: Optional[bool] = None
    rekenzone: int = 1            # tot welke rekenzone dit zonne-energiesysteem behoort (1..3)

@dataclass
class Installaties:
    # Primaire (1e) opwekkers blijven enkelvoudig zodat alle bestaande code (`installaties.verwarming...`)
    # blijft werken. EXTRA exemplaren (hybride WP+ketel, 2e boiler, 2e koeling) komen in de *_extra-lijsten;
    # de generators lopen er apart over / flaggen ze. PV is van nature al een lijst (meerdere PV-systemen).
    verwarming: Verwarming = field(default_factory=Verwarming)
    tapwater: Tapwater = field(default_factory=Tapwater)
    koeling: Koeling = field(default_factory=Koeling)
    zonne_energie: List[ZonneEnergieSysteem] = field(default_factory=list)
    verwarming_extra: List[Verwarming] = field(default_factory=list)
    tapwater_extra: List[Tapwater] = field(default_factory=list)
    koeling_extra: List[Koeling] = field(default_factory=list)

@dataclass
class Berekening:
    kwh_m2_huidig: Optional[float] = None
    standaard_eis_kwh_m2: Optional[float] = None
    kwh_m2_na_maatregelen: Optional[float] = None
    label_huidig: str = ""
    bron: str = "Vabi EPA-W (NTA8800)"

@dataclass
class Subpost:
    """Meerwerk-regel binnen een maatregel: categorie 2 (foto-onderbouwd) of 3 (bijzonder)."""
    categorie: int = 2            # 2 | 3
    code: str = ""
    omschrijving: str = ""
    prijs_per_eenheid: Optional[float] = None
    eenheid: str = "m²"
    hoeveelheid: float = 0.0
    kosten: Optional[float] = None

@dataclass
class Maatregel:
    code: str = ""                # maatregelcode uit catalogus, bv. V1-1-A1
    onderdeel: str = ""           # A Gevel | B Glas en kozijnen | C Vloeren | D Daken | E Ventilatie
    omschrijving: str = ""
    materiaal: str = ""
    rc_u_doel: str = ""           # Rc of U-doelwaarde (string, want soms Rc soms U)
    oppervlakte_m2: float = 0.0
    eenheid: str = "m²"
    prijs_per_eenheid: Optional[float] = None
    kosten: Optional[float] = None
    categorie: int = 1            # 1/2/3 (hoofdregel = categorie 1)
    biobased: bool = False
    subposten: List[Subpost] = field(default_factory=list)  # cat 2/3 meerwerk (T7-T9)

@dataclass
class Haalbaarheid:
    maatregel_code: str = ""
    asbest: Optional[bool] = None
    lood: Optional[bool] = None
    bereikbaarheid: str = ""      # Goed | Hoogwerker | Steiger | Beperkt
    kruipruimte_diepte_cm: Optional[float] = None
    obstakels: str = ""
    vocht: Optional[bool] = None
    toelichting: str = ""

@dataclass
class Foto:
    bestand: str = ""
    bouwdeel: str = ""            # V1..V6
    type: str = "overzicht"      # overzicht | detail-cat2 | detail-cat3 | voorblad | huisnummer

@dataclass
class Validatie:
    status: str = "onbekend"      # sluitend | onvolledig | onbekend
    issues: List[str] = field(default_factory=list)

@dataclass
class Meta:
    catalogus_versie: str = ""
    gegenereerd_op: str = ""
    tool_versie: str = "0.1"

# ---------- hoofdobject ----------
@dataclass
class Dossier:
    schema_version: str = SCHEMA_VERSION
    identificatie: Identificatie = field(default_factory=Identificatie)
    adviseur: Adviseur = field(default_factory=Adviseur)
    opname: Opname = field(default_factory=Opname)
    geometrie: Geometrie = field(default_factory=Geometrie)
    schil: List[SchilDeel] = field(default_factory=list)
    ventilatie: Ventilatie = field(default_factory=Ventilatie)
    installaties: Installaties = field(default_factory=Installaties)
    berekening: Berekening = field(default_factory=Berekening)
    maatregelen: List[Maatregel] = field(default_factory=list)
    haalbaarheid: List[Haalbaarheid] = field(default_factory=list)
    fotos: List[Foto] = field(default_factory=list)
    validatie: Validatie = field(default_factory=Validatie)
    meta: Meta = field(default_factory=Meta)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Dossier":
        return _from_dict(Dossier, d)

# ---------- generieke (de)serialisatie ----------
def _from_dict(cls, d):
    if d is None:
        return cls()
    kwargs = {}
    type_hints = {f.name: f.type for f in fields(cls)}
    for f in fields(cls):
        if f.name not in d:
            continue
        val = d[f.name]
        ftype = f.type
        # lijsten van dataclasses
        if isinstance(val, list):
            inner = _list_inner_type(cls, f.name)
            if inner and is_dataclass(inner):
                kwargs[f.name] = [_from_dict(inner, x) for x in val]
            else:
                kwargs[f.name] = val
        else:
            inner = _field_dataclass_type(cls, f.name)
            if inner and isinstance(val, dict):
                kwargs[f.name] = _from_dict(inner, val)
            else:
                kwargs[f.name] = val
    return cls(**kwargs)

# expliciete type-mapping (robuuster dan string-hints parsen)
_DATACLASS_FIELDS = {
    "identificatie": Identificatie, "adviseur": Adviseur, "opname": Opname,
    "geometrie": Geometrie, "ventilatie": Ventilatie, "berekening": Berekening,
    "validatie": Validatie, "meta": Meta,
    "installaties": Installaties, "verwarming": Verwarming, "tapwater": Tapwater,
    "koeling": Koeling,
}
_LIST_FIELDS = {
    "schil": SchilDeel, "maatregelen": Maatregel, "haalbaarheid": Haalbaarheid,
    "fotos": Foto, "vloeren": VloerInfo, "ruimtes": Ruimte,
    "zonne_energie": ZonneEnergieSysteem, "subposten": Subpost,
    "verwarming_extra": Verwarming, "tapwater_extra": Tapwater, "koeling_extra": Koeling,
}
def _field_dataclass_type(cls, name): return _DATACLASS_FIELDS.get(name)
def _list_inner_type(cls, name): return _LIST_FIELDS.get(name)

def save_json(dossier: Dossier, path: str):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dossier.to_dict(), fh, ensure_ascii=False, indent=2)

def load_json(path: str) -> Dossier:
    with open(path, encoding="utf-8") as fh:
        return Dossier.from_dict(json.load(fh))

# ---------- voorbeelddossier (Essenhage 32, o.b.v. de .epa/monitor) ----------
def build_sample() -> Dossier:
    d = Dossier()
    d.identificatie = Identificatie(
        bag_vboid="0037010000368601", straat="Essenhage", huisnummer="32",
        postcode="9501TP", plaats="Stadskanaal", bouwjaar=1979,
        woningtype="Tussenwoning", aantal_bouwlagen=2)
    d.adviseur = Adviseur(naam="Renze Poortinga", bedrijf="Poortinga Energieadvies",
                          telefoon="0616691927", email="info@poortinga-energieadvies.nl")
    d.opname = Opname(opnamedatum="2026-02-24", rapportagedatum="2026-03-10",
                      type_advies="Basis", qv10_gemeten=False, bewijslast="Geen")
    d.geometrie = Geometrie(gebruiksoppervlakte_ag_m2=57.70, verwarmd_volume_m3=198.59,
                            perimeter_m=40.72,
                            vloeren=[VloerInfo("Begane grond", 56.31, 2.61)],
        ruimtes=[Ruimte("Woonkamer","verblijfsruimte",35.0), Ruimte("Keuken","keuken",8.0),
                 Ruimte("Slaapkamer 1","verblijfsruimte",12.0), Ruimte("Slaapkamer 2","verblijfsruimte",9.0),
                 Ruimte("Badkamer","badkamer",5.0), Ruimte("Toilet","toilet",1.5), Ruimte("Hal","verkeer",6.0)])
    d.schil = [
        SchilDeel(id="gevel-voor", type="gevel", subtype="Spouwmuur", begrenzing="Buitenlucht",
                  orientatie="Z", oppervlakte_m2=24.0, isolatie_aanwezig="Niet",
                  spouw_aanwezig=True, rc_huidig=0.43, rc_bron="Forfaitair bouwjaar"),
        SchilDeel(id="gevel-achter", type="gevel", subtype="Spouwmuur", begrenzing="Buitenlucht",
                  orientatie="N", oppervlakte_m2=24.0, isolatie_aanwezig="Niet",
                  spouw_aanwezig=True, rc_huidig=0.43, rc_bron="Forfaitair bouwjaar"),
        SchilDeel(id="vloer-bg", type="vloer", subtype="Begane grondvloer", begrenzing="Grond",
                  orientatie="horizontaal", oppervlakte_m2=56.31, isolatie_aanwezig="Niet",
                  rc_huidig=0.15, rc_bron="Forfaitair bouwjaar"),
        SchilDeel(id="dak", type="dak", subtype="Hellend dak", begrenzing="Buitenlucht",
                  orientatie="horizontaal", oppervlakte_m2=60.0, isolatie_aanwezig="Niet",
                  rc_huidig=0.86, rc_bron="Forfaitair bouwjaar"),
        SchilDeel(id="raam-z", type="kozijn", subtype="Raam", begrenzing="Buitenlucht",
                  orientatie="Z", oppervlakte_m2=13.54, glastype="Dubbel",
                  kozijnmateriaal="Hout", u_huidig=2.9),
    ]
    d.ventilatie = Ventilatie(systeem="C: natuurlijke toevoer, mechanische afzuiging",
                              systeem_soort="Individueel",
                              opmerkingen="Mechanische box; natuurlijke toevoer via roosters.")
    d.installaties = Installaties(
        verwarming=Verwarming(systeem="Individueel", type_opwekker="Gasgestookte ketel",
                              subtype="HR107", opstelplaats="Binnen thermische zone",
                              distributiemedium="Water", aanvoertemperatuur="90/70",
                              type_distributie="Tweepijpssysteem",
                              afgifte="Radiatoren / convectoren",
                              regeling="Regeling in hoofdvertrek (kamerthermostaat)"),
        tapwater=Tapwater(aantal_systemen=1, type_installatie="Individueel",
                          aangesloten_op="Hele woning", type_opwekker="Compleet toestel",
                          type_toestel="Gasgestookt combitoestel",
                          gaskeur="Met Gaskeur HR en CW", cw_klasse="CW-4/5/6",
                          dwtw_aanwezig=False, lengte_keuken="4 m <= l < 6 m",
                          lengte_badkamer="l < 4 m"),
        koeling=Koeling(aanwezig=False), zonne_energie=[])
    d.berekening = Berekening(kwh_m2_huidig=121.09, standaard_eis_kwh_m2=70.0,
                              kwh_m2_na_maatregelen=None, label_huidig="B")
    d.maatregelen = [
        Maatregel(code="V1-1-A1", onderdeel="A Gevel", omschrijving="Spouwmuurisolatie",
                  materiaal="EPS-parels", rc_u_doel="Rc 1,7", oppervlakte_m2=48.0,
                  eenheid="m²", categorie=1),
        Maatregel(code="V3-1", onderdeel="C Vloeren", omschrijving="Vloerisolatie (bodem)",
                  materiaal="—", rc_u_doel="Rc 3,5", oppervlakte_m2=56.31, eenheid="m²", categorie=1),
        Maatregel(code="V4-1", onderdeel="D Daken", omschrijving="Dakisolatie hellend (binnenzijde)",
                  materiaal="—", rc_u_doel="Rc 3,5", oppervlakte_m2=60.0, eenheid="m²", categorie=1),
    ]
    d.haalbaarheid = [
        Haalbaarheid(maatregel_code="V3-1", kruipruimte_diepte_cm=45, bereikbaarheid="Goed",
                     asbest=False, vocht=False, toelichting="Kruipruimte toegankelijk en droog."),
    ]
    d.fotos = [Foto(bestand="huisnummer.jpg", bouwdeel="-", type="huisnummer"),
               Foto(bestand="voorgevel.jpg", bouwdeel="-", type="voorblad")]
    d.meta = Meta(catalogus_versie="V3_Q2_03062026",
                  gegenereerd_op=datetime.date.today().isoformat(), tool_versie="0.1")
    return d

# ---------- minimaal JSON Schema (documentatie/validatie) ----------
def json_schema() -> dict:
    def obj(props, req=None):
        return {"type": "object", "properties": props, "required": req or []}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Nij Begun & EPA canoniek dossier",
        "version": SCHEMA_VERSION,
        "type": "object",
        "required": ["identificatie", "schil"],
        "properties": {
            "schema_version": {"type": "string"},
            "identificatie": obj({
                "bag_vboid": {"type": "string"}, "postcode": {"type": "string"},
                "huisnummer": {"type": "string"}, "bouwjaar": {"type": ["integer", "null"]},
                "renovatiejaar": {"type": ["integer", "null"]},
                "woningtype": {"type": "string"}}, ["postcode", "huisnummer"]),
            "adviseur": {"type": "object"},
            "opname": {"type": "object"},
            "geometrie": {"type": "object"},
            "schil": {"type": "array", "items": obj({
                "type": {"enum": ["gevel", "vloer", "dak", "kozijn"]},
                "begrenzing": {"type": "string"}, "oppervlakte_m2": {"type": "number"},
                "rc_huidig": {"type": ["number", "null"]}, "u_huidig": {"type": ["number", "null"]}})},
            "ventilatie": {"type": "object"},
            "berekening": {"type": "object"},
            "maatregelen": {"type": "array", "items": obj({
                "code": {"type": "string"}, "onderdeel": {"type": "string"},
                "oppervlakte_m2": {"type": "number"}, "kosten": {"type": ["number", "null"]}})},
            "haalbaarheid": {"type": "array"},
            "fotos": {"type": "array"},
            "validatie": {"type": "object"},
            "meta": {"type": "object"},
        },
    }

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    sample = build_sample()
    save_json(sample, os.path.join(root, "sample_dossier.json"))
    with open(os.path.join(here, "canonical_schema.json"), "w", encoding="utf-8") as fh:
        json.dump(json_schema(), fh, ensure_ascii=False, indent=2)
    # round-trip sanity
    rt = Dossier.from_dict(sample.to_dict())
    assert rt.to_dict() == sample.to_dict(), "round-trip mismatch"
    print("OK: sample_dossier.json + core/canonical_schema.json geschreven; round-trip klopt.")
    print(f"  schil-delen: {len(sample.schil)} | maatregelen: {len(sample.maatregelen)}")
