# Mappingoverzicht (gegenereerd)

**NIET handmatig bewerken** — dit bestand wordt gegenereerd uit `core/mapping_manifest.py`
via `python scripts/check_mapping_manifest.py --write-doc`. Wijzig het manifest, niet deze
tabel; `--check-doc` faalt luid als ze uit elkaar lopen.

## begrenzing

| | |
|---|---|
| Bronform | Constructies (project) + Gevel per wand / Vloer per kamer / Deur (element) |
| Bronlabel | Gevel - begrenzing · Vloer - begrenzing · Begrenzing (anders dan buitenlucht) |
| Verplicht | conditioneel: alleen tonen als niet Buitenlucht |
| Canoniek dossierveld | `SchilDeel.begrenzing` |
| Parser-normalisatie | `magicplan.statistics_csv:_BEGR_CANON` |
| Webapp-opties | `dashboard.app:BEGR_OPTS` |
| VABI-pad | Objecten > Hoofdvlak > GrenstAan |
| VABI-codes | `vabi.objecten_generate:_grenst_aan_code` |
| VABI-codes normalizer | — |
| Bewust onbevestigde opties | — |
| Bewijsstatus | **bevestigd** |
| Bron | vabi/refs/grenstaan_mapping.md; volledige dropdown 0-9 live afgelezen EPA 12.0.1 (19-7-2026) |

## glastype

| | |
|---|---|
| Bronform | Raam/paneel + Deur (element) |
| Bronlabel | Type glas · Type glas (indien glas in deur) · Bovenlicht deur - type glas |
| Verplicht | verplicht (hoofdraam) / conditioneel (bovenlicht/deur) |
| Canoniek dossierveld | `SchilDeel.glastype` |
| Parser-normalisatie | `magicplan.statistics_csv:_GLAS_CANON` |
| Webapp-opties | `dashboard.app:GLAS_OPTS` |
| VABI-pad | Constructiebibliotheek > Constructie(Raam) > Glas (via vabi.codebook.Codebook.glas_code) |
| VABI-codes | `vabi.codebook:Codebook.glas_code` |
| VABI-codes normalizer | `vabi.constructie_generate:_norm_glas` |
| Bewust onbevestigde opties | Onbekend |
| Bewijsstatus | **bevestigd** |
| Bron | vabi/codebook.py leidt de codes zelf af uit vabi/refs/standaard_constructies_v120001001.xml (219 constructies); 'Onbekend' wordt bewust NIET gegokt (generator-issue, audit-glas-F3 15-7) |

## kozijnmateriaal

| | |
|---|---|
| Bronform | Raam/paneel + Deur (element) |
| Bronlabel | Kozijnmateriaal |
| Verplicht | optioneel (default Hout of kunststof) |
| Canoniek dossierveld | `SchilDeel.kozijnmateriaal` |
| Parser-normalisatie | `magicplan.statistics_csv:_KOZIJN_MAT` |
| Webapp-opties | `dashboard.app:KOZ_OPTS` |
| VABI-pad | Constructiebibliotheek > Constructie(Raam/Deur) > Kozijn (via vabi.codebook.Codebook.kozijn_code) |
| VABI-codes | `vabi.codebook:Codebook.kozijn_code` |
| VABI-codes normalizer | `vabi.constructie_generate:_norm_kozijn` |
| Bewust onbevestigde opties | — |
| Bewijsstatus | **bevestigd** |
| Bron | vabi/codebook.py (zelfde export als glastype); labels incl. haakjes = NTA 8.3 kozijntype A/B/C, letterlijk het live MagicPlan-optielabel (docs/magicplan-forms-live.md) |

## gevel_orientatie

| | |
|---|---|
| Bronform | Object (project) + Gevel per wand (override) |
| Bronlabel | Oriëntatie voorgevel · Gevel - oriëntatie (override) |
| Verplicht | verplicht (voorgevel) |
| Canoniek dossierveld | `SchilDeel.orientatie` |
| Parser-normalisatie | — |
| Webapp-opties | `dashboard.app:ORI_OPTS` |
| VABI-pad | Objecten > Hoofdvlak > Orientatie (Geometrie-tabblad) |
| VABI-codes | `vabi.objecten_generate:ORIENTATIE_CODE` |
| VABI-codes normalizer | — |
| Bewust onbevestigde opties | — |
| Bewijsstatus | **bevestigd** |
| Bron | Geometrie-export voorbeeldproject 'hoekwoning' (18-7-2026): Zuid=0/Noord=4/Oost=6 rechtstreeks bevestigd, rest via dropdownvolgorde |

## woningtype_subtype

| | |
|---|---|
| Bronform | Object (project) |
| Bronlabel | Woningtype |
| Verplicht | verplicht |
| Canoniek dossierveld | `Identificatie.woningtype` |
| Parser-normalisatie | — |
| Webapp-opties | `dashboard.app:WONINGTYPE_OPTS` |
| VABI-pad | Objecten > Object > Subtype (woningpositie; Gebouwtype vast 0=Eengezinswoning, Nij Begun-scope) |
| VABI-codes | `vabi.objecten_generate:_subtype_code` |
| VABI-codes normalizer | — |
| Bewust onbevestigde opties | Galerijwoning, Portiekwoning, Maisonnette (bovenwoning), Woning boven bedrijfsruimte, Appartement (tussen), Appartement (hoek) |
| Bewijsstatus | **gedeeltelijk** |
| Bron | Objecten-export hoekwoning (Subtype=1) + monitor-fixture tussenwoning (Subtype=2), 18-7-2026; alle 6 meergezins-varianten vallen buiten de Nij Begun-scope (grondgebonden eengezinswoningen) en worden bewust NIET gegokt (golden rule; _subtype_code() sloot 'appartement' expliciet uit na een mappingmanifest-audit 21-8: 'Appartement (tussen)'/'(hoek)' matchten eerder per ongeluk de grondgebonden hoek/tussen-substring-check) |

## pv_orientatie

| | |
|---|---|
| Bronform | Installaties > ZONNE-ENERGIE (project) |
| Bronlabel | PV - oriëntatie |
| Verplicht | conditioneel: alleen als PV aanwezig |
| Canoniek dossierveld | `ZonneEnergieSysteem.orientatie` |
| Parser-normalisatie | — |
| Webapp-opties | — |
| VABI-pad | Installatiebibliotheek > ZonneEnergie > Orientatie (LET OP: eigen enum, 0=N startend, ANDERS dan de geometrie-Orientatie) |
| VABI-codes | `vabi.installatie_generate:PV_ORIENTATIE` |
| VABI-codes normalizer | — |
| Bewust onbevestigde opties | — |
| Bewijsstatus | **bevestigd** |
| Bron | PV end-to-end geverifieerd (22-6-2026): 12x1,70=20,40 m2 PV/Zuid/35 graden foutloos geimporteerd in EPA |
