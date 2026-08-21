# 0002 — Ventilatieberekening blijft afronden op 0,1 l/s

**Context.** Bij het naberekenen van een concurrerend product (Aira, zie
`docs/ventilatieplan-webapp-spec.md` §1) bleek hun rekenhart identiek aan
`ventilatie/ventilatie.py`: dezelfde 0,7 dm³/s·m² per verblijfsgebied, hetzelfde
minimum van 7 l/s per leefruimte en dezelfde afvoerminima (keuken 21 / bad 14 /
toilet 7). Het enige verschil: zij ronden elke l/s-waarde af naar het
dichtstbijzijnde hele getal (12,74 → 13,0; 8,54 → 9,0; 40,04 → 40,0). Wij
ronden nu op 0,1 l/s (taak 019, Notes).

**Overwogen.** Hele l/s leest prettiger op een tekening en ligt aan de veilige
kant bij de capaciteitsvraag (naar boven afronden zou dat zijn; Aira rondt
gewoon wiskundig af, dus niet per se veiliger). Maar: elke bestaande
dossier-JSON, elk gegenereerd rapport en elke test die op de huidige 0,1-
precisie steunt verandert van uitkomst zodra de afronding wijzigt. Dat is een
zichtbare wijziging voor lopende projecten, niet iets om terloops in een
uitbreidingstaak (019) mee te nemen.

**Besluit.** `ventilatie/ventilatie.py` blijft afronden op 0,1 l/s. Taak 019
bouwt de balansverdeling, deurbelasting en vuistregeltoets op deze precisie.
Overstappen naar hele l/s (zoals Aira) is een aparte, expliciete beslissing —
pas nemen wanneer er een concrete reden is (bijvoorbeeld: de tekenlaag uit
taak 020 blijkt met hele getallen prettiger leesbaar) en met een eigen taak
die de impact op bestaande dossiers in kaart brengt.

**Gevolgen.** De testfixture "demo-woning" uit de spec (Aira's eigen
voorbeeld) wordt overgenomen met ónze afronding, niet met hun hele getallen —
zie de acceptatiecriteria in `tasks/active/019-ventilatie-rekenlaag-uitbreiden.md`.
