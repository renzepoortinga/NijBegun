# Overdracht nieuwe structuur — 12 augustus 2026

## Managementconclusie

De nieuwe structuur is technisch doorgevoerd en bruikbaar als basis voor de werksessie. De regressiesuite slaagt volledig (**713 geslaagd, 0 gefaald**) en het package `nijbegun-engine` bouwt succesvol als wheel.

De code is helder verdeeld over een canoniek domeinmodel, opname/import, VABI-uitwisseling, maatregellogica, catalogus, validatie, documentgeneratie en dashboard. De belangrijkste resterende risico's zitten niet in de mapstructuur zelf, maar in overdrachtsdocumentatie, bronversiebeheer en live validatie van externe koppelingen.

## Verificatie

Uitgevoerd vanuit de repository-root:

```powershell
python -m pip install -r requirements.txt
python tests/run_tests.py
python -m build --wheel
```

Resultaat:

- regressietests: 713/713 groen;
- wheel-build: `nijbegun_engine-0.1.0-py3-none-any.whl` succesvol;
- Git-worktree vóór deze documentatie-aanpassing: schoon;
- actieve branch: `main`;
- canonieke package-interface aanwezig in `nijbegun_engine/`.

## Wat goed is doorgevoerd

- Eén canoniek dossier in `core/` als interne waarheid.
- MagicPlan-import is gescheiden van domein- en rekenlogica.
- VABI-formaten en enums zijn geïsoleerd in `vabi/`.
- Advieslogica en catalogusdata hebben afzonderlijke verantwoordelijkheden.
- Dashboard gebruikt de gedeelde modules in plaats van een tweede rekenkern te vormen.
- Package-configuratie neemt de interne modules en benodigde package-data mee.
- De gouden regel is in code en documentatie zichtbaar: VABI blijft de geattesteerde NTA 8800-rekenkern.
- Recente regressies bewaken onder meer vocabulaire, stille defaults, geometrie, glas, ventilatie en dubbele ruimten.

## Oranje punten voor de werksessie

1. **README en BUILD_LOG zijn deels historisch.** Ze noemen nog `tool/`, bovenliggende voorbeeldbestanden en oude TODO's die inmiddels zijn gerealiseerd. Behandel `BUILD_LOG.md` als historisch logboek, niet als actuele backlog.
2. **Bronversies ontbreken centraal.** Leg exacte versies/peildata vast van NTA 8800, ISSO, BRL, Nij Begun-documenten, catalogus en VABI-attest/handleiding. Zie het bronregister in `HERKOMST-ENERGIELABEL-NTA-ISSO-NIJ-BEGUN.md`.
3. **Live koppelingen blijven apart te accepteren.** Offline tests bewijzen niet dat MagicPlan, Microsoft Graph/BAG, VABI-import en Nij Begun-portaal op de dag van gebruik ongewijzigd zijn.
4. **Documentatie bevat bewuste handmatige stappen.** Meerdere invoeren worden terecht geflagd voor controle in VABI. Maak hiervan geen automatische default zonder primaire bron en regressietest.
5. **Versie is nog 0.1.0.** Spreek af wanneer de structuur stabiel genoeg is voor 0.2.0 en welke acceptatiecriteria daarbij horen.

## Voorgestelde agenda voor morgen

1. Loop één echt dossier end-to-end door: opname → canoniek dossier → VABI huidige staat → maatregelen → VABI toekomstige staat → isolatieplan/export.
2. Controleer iedere gele/handmatige VABI-actie en noteer of deze noodzakelijk, automatiseerbaar of verouderd is.
3. Vul samen het bronregister met de documenten die lokaal beschikbaar zijn.
4. Vergelijk de actuele Nij Begun-catalogus en formats met de in de repository vastgelegde versies.
5. Maak na de sessie één geprioriteerde backlog: blokkerend voor productie, nodig voor kwaliteit, en later optimaliseren.

## Definitie van “klaar voor productie”

De mapstructuur alleen is niet voldoende. Productiegereed betekent minimaal:

- een echt dossier zonder onverwachte handmatige reparaties door de keten;
- formele uitkomsten aantoonbaar uit de geattesteerde VABI-versie;
- exacte bron- en softwareversies in het dossier;
- alle aannames zichtbaar en door een bevoegde adviseur beoordeeld;
- leverdocumenten compleet volgens het actuele Nij Begun-format;
- herstelbare opslag, toegangsbeveiliging en dossierbewaring geregeld;
- wijzigingen traceerbaar via Git en afgedekt met regressietests.

