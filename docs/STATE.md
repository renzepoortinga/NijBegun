# STATE — dashboard

> Dit is een overzicht, geen administratie. De taken zelf staan in `tasks/`.
> Houd dit kort: als het langer wordt dan één scherm, hoort iets in een taakbestand.

Bijgewerkt: 2026-08-21 door Codex (taak 016 afgerond)

## Nu
De keten werkt end-to-end: MagicPlan-opname → canoniek dossier → alle drie
VABI-bibliotheken (foutloos importeerbaar in EPA 12.0.1) → isolatieplan
(Word/PDF) + ventilatie + fotochecklist + KWACO-validatie, met een lokaal
dashboard. De volledige suite is omgevingsonafhankelijk en de Python-testcheck in
`verify.sh` is blocking. Historie staat in `BUILD_LOG.md` en
`STATUS_NACHT_2026-06-13.md`; vanaf nu is dít bestand + `tasks/` de stand.

## Actief
Zie `tasks/active/`. Draai `./scripts/status.sh` voor het actuele beeld.

Taak 016 (veilige one-click MagicPlan-intake) is afgerond: pakketten krijgen identiteit- en
fingerprintgates, een hashgebonden merged preview en een per-project CAS-bevestiging. Herimport
behoudt expliciet handmatig werk/resultaten; ZIP, schema en metrische geometrie zijn fail-closed.
Vijf reviewrondes; eindverdict PASS, 998/998 groen.

Taak 021 (ventilatieplan PDF/PNG-export) is afgerond: scherm en export delen één scene, de PDF bevat
voorblad, vloerpagina's, een dynamisch gepagineerde berekening en vaste paginavoeten; per vloer is een
1200x900-PNG beschikbaar. JPEG en gangbare PNG-varianten worden veilig via Pillow gerenderd.
Blocking verify en onafhankelijke herreview: PASS (1020/1020).

Taak 020 (interactief ventilatieplan) is afgerond: ruimtepolygonen worden expliciet gekalibreerd,
markers blijven ruimte- en verdiepingsgebonden, overstroom volgt pas na expliciete topologie en
deurbelasting wordt correct getoetst. Pointer- en toetsenbordbediening, concave geometrie en strikte
polygonvalidatie zijn gedekt. Vijf reviewrondes; eindverdict PASS, 957/957 groen.

Taak 023 (legacy-dakkapel en dakpreflight) is afgerond: een ongetagd legacy-moederdak wordt na
dakkapelbewerking correct herclassificeerd. Samengestelde Vabi-export scant de dubbele-dakpoort
exact eenmaal via private kernen; publieke writers blijven altijd fail-closed. Herreview PASS,
851/851 groen.

Taak 016 (veilige one-click MagicPlan-intake) is gebouwd op de featurebranch: offline
ZIP-pakket met project-/woningidentiteitsgate, formfingerprint, preview/diff, expliciet
behoudbeleid en gegroepeerde resttaken. De vooraf vastgelegde referentiecase en volledige
dry-run zijn groen; onafhankelijke AI-review staat nog open.

Taak 015 (mappingmanifest en MagicPlan-formulierfingerprint) is afgerond: zes kritieke
dropdownketens verwijzen naar de echte parser/webapp/Vabi-code en naar een gereviewd
formulier-snapshotcontract. Optie-, label- en overige snapshotdrift maken CI luid rood.
Alle importpaden bewaren fingerprint/importmetadata; onafhankelijke herreview PASS, 845/845 groen.

Taak 024 onderzoekt en importeert de actuele maatregelencatalogus uit de publieke Nij Begun API.
De API heeft specversie 1.0 maar geen inhoudelijk versielabel; de import wordt daarom vastgelegd
met ophaaltijd en contentfingerprint. De eerste live vergelijking vond 291 API-regels tegenover
338 XLSX-regels. Publicatie is geblokkeerd doordat de API code `V1-2-X3` zowel als rolsteiger
(EUR 250,43/st) als hoogwerker (EUR 569,25/wk) levert; de geldige XLSX-snapshot blijft actief.

Taak 017 (atomische Vabi-exportset) is afgerond: writers publiceren eerst een gevalideerde,
immutable set en maken die zichtbaar via één atomische `CURRENT.json`-wissel. Fouten behouden
de vorige geldige set; dashboarddownloads en projectexport volgen CURRENT met legacyfallback.
Traversal, writer-/manifestfouten en concurrency hebben regressiedekking. AI-herreview: PASS.

Taak 018 (aanvoertemperatuur-normalisatie) is afgerond: dotted MagicPlan-waarden zoals
`90.70` blijven intact tot de gerichte Vabi-normalisatie en worden voor alle 12 ondersteunde
codes correct geëxporteerd zonder onbekend-flag. Onafhankelijke AI-review: PASS.

Taak 001 (nulmeting en repositorygate) is afgerond: `main` is groen met 786/786 tests en
branch protection vereist voortaan een actuele, geslaagde `verify`-check. De regel geldt ook
voor admins; force-push en branch deletion zijn uitgeschakeld. Onafhankelijke AI-review: PASS.

Taak 002 (draagbare tests) is afgerond: de plan-JSON- en loginchecks gebruiken eigen fixtures,
de suite is 786/786 groen en `verify.sh` blokkeert weer op Python-testfalen. Onafhankelijke
AI-review: PASS.

Taak 013 (ketenaudit MagicPlan → tool → Vabi) en taak 014 (dakmigratie zonder dubbele
legacyvlakken — het Essenhage-dakdubbelingspatroon uit taak 013) zijn afgerond en staan in
`tasks/done/`. Vervolgbevindingen staan als taak 023 (dakkapel/preflight) en 025
(MagicPlan-SSL) in `backlog/`.

Taak 020 (ventilatieplan-pagina in de webapp) is na review-FAIL heropend en staat in `tasks/active/`.
De blockers zijn gerepareerd en na integratie met taak 015 zijn 957/957 tests groen;
onafhankelijke herreview staat nog open.
De taak levert route `/project/<tag>/ventilatieplan` (GET pagina + POST markers +
POST herstel) bovenop de taak-019-rekenlaag. Dossier minimaal uitgebreid (`core/dossier.py`):
`Ruimte.verdieping`, `VloerInfo.plattegrond_afbeelding` (forward-compat taak 022) en de nieuwe
`Ventilatieplan`/`VentilatieplanVerdieping`/`VentilatieMarker`-dataclasses. Nieuwe pure datalaag
`dashboard/ventilatieplan.py` (groeperen per verdieping, autoplaatsing inclusief overstroom bij de
bronruimte zonder een onbekende deurverbinding te verzinnen, batch- en verdiepingvalidatie) +
`dashboard/static/ventilatieplan.js` (vanilla JS: ruimtepolygon-hit-test, highlight/koppellijn,
rollback buiten een ruimte en dubbelklik=wijzigen/verwijderen/splitsen). Een eerdere AI-review vond
2 restbevindingen in `ventilatie/ventilatie.py` (taak 019:
misleidende '0 m2'-waarschuwing bij een negatief oppervlak, `deurbelasting()` valideerde niet het
hele overstroompad) — beide gefixt op deze branch. Blocking verify PASS. Geen browser-visuele-QA:
de browserruntime meldde nul beschikbare browsers. Vervolgtaken 021
(PDF/PNG-export) en 022 (plattegrond uit foto) staan in backlog, buiten scope van 020.

Taak 019 (ventilatie-rekenlaag uitbreiden: balans, deurbelasting, vuistregeltoets) is afgerond en
staat in `tasks/done/`: eerst de afrondingsbeslissing vastgelegd in `docs/decisions/0002-ventilatie-
afronding.md` (blijft 0,1 l/s). Daarna `ventilatie/ventilatie.py` uitgebreid met `verdeel_balans()`
(afvoer per natte ruimte proportioneel opgehoogd tot de som gelijk is aan de toevoer, grootste-
restmethode zodat niemand door afronding onder zijn minimum zakt), een `afvoerpunt`-vlag,
`toevoer_herkomst`/`afvoer_herkomst` per regel (oppervlakte/minimum/balansophoging — nooit meer zonder
herkomst) en `deurbelasting()`/`toets_vuistregels()` voor alle 7 Nij Begun-vuistregels; ontbrekende
geometrie/installatiekeuzes geven altijd 'niet te bepalen', nooit een stille 'voldoet'. AI-review vond
3 echte punten (rondingsfout in de balansverdeling, stille fantoom-toevoer-onderdrukking, silent
fallback in deurbelasting), alle drie gefixt. 825/825 tests groen; `verify.sh` PASS. Vervolgtaken 020
(webapp-pagina) en 021 (export) staan in backlog, buiten scope van 019.

Taak 003 (kwaliteitsverklaring in `SchilDeel.rc_bron` blokkeert Vabi-export)
is afgerond en staat in `tasks/done/`: onafhankelijke herreview van commit
`4dd8221` met VERDICT PASS.

Taak 004 (visuele laag SVG voor dak/dakkapel + gebouwoverzicht) is klaar en
staat in `tasks/done/`: 4 reviewrondes (Codex), laatste VERDICT PASS. Onderweg
ontdekt en meegefixt: een bestaande test in `tests/run_tests.py` verwachtte
nog het oude gedrag van `vabi/constructie_generate.write()` vóór taak 003 —
crashte de testrunner stil, waardoor `verify.sh` een tijdje geen volledige
testrun meer liet zien. `python tests/run_tests.py`: 733/733 groen.

Taak 005 (isometrische dak- en dakkapelwizards) is klaar en staat in
`tasks/done/`: dependencyvrije 3D→2D-projectie, live maatvaste previews,
renderingmetadata inclusief geometriegroepen/moederdakreferentie en identieke
client/servervalidatie voor asymmetrische en steile daken. Onafhankelijke
review op commit `9734d09`: PASS. `python tests/run_tests.py`: 742/742 groen.

Taak 006 (isometrisch gebouwoverzicht) is klaar en staat in `tasks/done/`:
vier consistente MagicPlan-gevels leveren een maatvaste isometrische box;
onvolledige/inconsistente invoer krijgt een expliciete niet-3D fallback.
Taak-005-daken renderen exact na geometrievalidatie, legacy-daken zichtbaar
benaderd en dakkapellen via hun moederdakrelatie. Onafhankelijke herreview op
commit `e157ce0`: PASS MET RISICO'S, geen blockers. 746 checks groen; lokaal
blijven uitsluitend de twee bekende taak-002-omgevingschecks over.

Taak 007 (gebouwoverzicht op de echte MagicPlan-plattegrondcontour) is klaar
en staat in `tasks/done/`: `magicplan/assemble.py` leest nu de tot dusver
ongebruikte `image_map`-plattegrondcontour uit MagicPlans API en kalibreert
'm op `statistics.area_with_walls` (met plausibiliteitscheck tegen de
netto-oppervlakte); `dashboard/gebouw_svg.py` tekent die echte (ook
niet-rechthoekige) vorm wanneer beschikbaar, met een schoenveter-teken-
gebaseerde backface-culling die ook bij een concaaf grondvlak correct is.
Zonder contour blijft het rechthoek-pad uit taak 006 de fallback. Het dak
volgt nog de bounding-box, niet de polygon zelf (bewust uit scope). AI-review
(`/code-review high`) vond 9 punten, waarvan 7 verwerkt (incl. een echte
normaal-bug bij concave vormen) en 2 bewust laten staan (lage impact, zie
taakbestand). 768/768 tests groen.

Taak 008 (dak-wizards erven de Constructies-DAK-standaard + bouwjaarklasse/rc_bron in de editor)
is klaar en staat in `tasks/done/`: de zadeldak- en freeform-dakwizard hardcodeerden nog
`isolatie_aanwezig="Onbekend"` i.p.v. `dos.opname.dak_standaard` te erven (het platte dak deed dit
al); nu alle drie via een gedeelde `_erf_dak_kwargs()`-helper. Bouwjaarklasse en Rc-bron zijn nu
ook per vlak zichtbaar/corrigeerbaar in de gebouwboom-editor. `docs/magicplan-velden-audit.md`
bevinding C bleek bij het narechecken al opgelost. AI-review vond 2 punten in een niet-aangeraakt
bestand (`scripts/verify.sh`, al vóór deze sessie ongecommit — zie Blokkades) en 1 terechte
duplicatie in eigen werk, verwerkt. 772/772 tests groen.

Taak 009 (fix verweesde-worktrees-check in `verify.sh`) is klaar en staat in `tasks/done/`: de
awk-padsplitser die stukliep op een spatie in het pad, en de `main`-worktree die zichzelf altijd
als "al gemerged, opruimen" meldde — beide empirisch gereproduceerd (tijdelijke worktree onder een
pad met spatie) en gefixt. AI-review vond nog een kleine efficiëntie-nit (`git rev-parse` gehoist
uit de loop), verwerkt.

Taak 010 (richtingsafhankelijke shading + grondschaduw — eerste stap visuele stijl-slag) is klaar
en staat in `tasks/done/`: elk vlak in het gebouwoverzicht + de drie dak-wizard-previews krijgt nu
een CSS `brightness()`-filter uit de vlaknormaal t.o.v. een vaste lichtrichting, bovenop de
bestaande kleurtokens (geen hex). AI-review vond 2 echte bugs (shading omgekeerd bij een met-de-
klok-mee aangeleverde MagicPlan-contour; grondschaduw werd een lichte halo in donker thema), beide
gefixt. Geen browser-visuele-QA — de Claude-in-Chrome-extensie verbond niet vanuit deze sessie
(zie Blokkades). 773/773 tests groen.

Taak 011 (stresstest contour-/gebouwoverzicht-pijplijn) is klaar en staat in `tasks/done/`: op
verzoek zelf gefuzzed i.p.v. te wachten op de volgende reviewronde. 300 willekeurige polygon-/
dakcombinaties op `gebouw_svg.py` gaven 0 fouten (kerngeometrie staat stevig); adversariële/
edge-case invoer op de databoundary (`magicplan/assemble.py`) vond wél 9 echte problemen over
2 rondes — NaN/Infinity en niet-numerieke (string) waarden in MagicPlan-API-velden
(`area_with_walls`/`area`/`ceilingHeight`/raammaten) die niet gevangen werden en ofwel crashten
ofwel stil doorlekten naar de opgeslagen `dossier.json`. Alle 9 gefixt (gedeelde `_getal()`-helper
i.p.v. losse patches), regressietests toegevoegd. 787/787 tests groen.

Taak 012 (live MagicPlan-API-calls faalden op Python 3.14, SSL-profielcheck) is klaar en staat in
`tasks/done/`: `python magicplan/extractor.py` faalde met `ssl.SSLCertVerificationError` — Python
3.13+/OpenSSL 3.2+ zet `VERIFY_X509_STRICT` standaard aan, en cloud.magicplan.app's certificaatketen
is niet 100% RFC-5280-profiel-conform (bevestigd géén MITM/proxy: curl/Windows accepteren dezelfde
keten, google.com werkte al via Python). Gefixt door precies die ene profielvlag uit te zetten,
verder niets aan certificaatverificatie veranderd. **Meteen live beproefd**: Essenhage 32
opnieuw opgehaald, de contour (taak 007) bleek daadwerkelijk te werken — 31-punts grondvlak i.p.v.
de platte doos, incl. de "berging" (MagicPlan: "Laundry Room", bevestigd via screenshot). Het
PRODUCTIEDOSSIER van dat project is chirurgisch bijgewerkt (alleen `contour_m` toegevoegd, niet de
rest van de opname vervangen zoals de normale JSON-upload zou doen), met backup + verificatie in
de draaiende container. AI-review vond de fix eerst onvolledig (`--probe`-route gemist), verwerkt.
790/790 tests groen.

## Blokkades
- Claude-in-Chrome-extensie verbond niet vanuit deze sessie (meerdere pogingen) — visuele QA van
  taak 010 is daarom numeriek/geometrisch geverifieerd, niet met een screenshot. Renze: bekijk het
  gebouwoverzicht + de dak-wizard-previews in de echte webapp voor het definitieve visuele oordeel.

## Openstaande beslissingen
- Geen.

## Technische schuld
- `CLAUDE.md` is 465 regels operationeel geheugen; werkt, maar migreer
  stukken naar `docs/` wanneer je ze toch aanraakt (geen aparte
  verbouwtaak waard op dit moment).
- Gebouw-SVG gebruikt een vaste paintervolgorde; uitzonderlijke samengestelde
  geometrie kan daardoor visueel overlappen. Legacy renderingmetadata met
  niet-eindige getallen heeft nog geen eigen defensieve foutstaat.

## Niet doen
- Geen nieuwe dependencies zonder overleg.
- Nooit zelf NTA 8800 rekenen — Vabi EPA-W is de rekenkern (gouden regel).
