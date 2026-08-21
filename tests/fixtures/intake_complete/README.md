# Complete offline referentie-intake (taak 016)

Dit contract lag vóór de implementatie vast. Het pakket gebruikt de bestaande
`../statistics_voorbeeld.csv` als Statistics-export, naast de projectidentiteit,
het rapport en de echte grondvlakcontour in deze map. `__CURRENT_SNAPSHOT__`
wordt bij het bouwen van de test-ZIP vervangen door de gecommitte fingerprint;
er is geen live API-call.

De volledige dry-run moet exact `expected.json` opleveren. Met name blijft de
dakcontrole open: Statistics levert geen betrouwbare dakgeometrie, zodat de
adviseur die expliciet in de webapp-wizard vastlegt en controleert.
