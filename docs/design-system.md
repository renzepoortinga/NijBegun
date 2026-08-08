# Design contract

Geen adjectieven. Elke regel is toetsbaar — machinaal of door de visual-QA-agent.

## Spacing
Uitsluitend tokens. Veelvouden van 4px, bij voorkeur 8. Geen losse pixelwaarden
in componenten.  → BLOCKING

## Typografie
Uitsluitend tokens. Eén schaal. Geen losse `font-size` in componenten.
Regellengte 60–75 tekens in lopende tekst.  → BLOCKING (tokens) / ADVISORY (lengte)

## Kleur
Uitsluitend tokens, geen hex-waarden in componenten. Contrast minimaal WCAG AA
(4.5:1 voor tekst). `prefers-color-scheme` wordt gerespecteerd.  → BLOCKING

## Aanraken en focus
Aanraakdoelen minimaal 44×44px. Zichtbare focus-state op alles wat bedienbaar is.
`outline: none` alleen met een expliciete vervanging.  → BLOCKING

## Beweging
150–300ms, ease-out bij verschijnen. `prefers-reduced-motion` wordt
gerespecteerd.  → BLOCKING (reduced-motion) / ADVISORY (timing)

## Responsive
Mobile-first. Getoetst op 390 / 768 / 1024 / 1440. Nooit horizontaal scrollen.
`env(safe-area-inset-*)` gerespecteerd.  → VISUAL QA

## Staten
Elk component dat data laadt heeft alle vier: leeg, laden, fout, gevuld.
Ontbreekt er één, dan is het component niet af.  → VISUAL QA

## Destructieve acties
Verwijderen, betalen en onomkeerbare acties vragen altijd om bevestiging.
De bevestiging benoemt wat er precies gebeurt.  → REVIEW

## Navigatie
Eén patroon per niveau. Terug is altijd voorspelbaar. Geen doodlopende
schermen zonder uitweg.  → VISUAL QA

## Hiërarchie
Per scherm één primaire actie, visueel duidelijk zwaarder dan de rest.  → VISUAL QA
