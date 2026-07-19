# Microsoft Graph-koppeling voor het gedeelde postvak — instructie voor de IT-beheerder

**Voor wie:** de beheerder van de Microsoft 365-omgeving van Poortinga Energieadvies.
**Doel:** een interne toepassing mag de toewijzingsmails uit het **gedeelde postvak
`info@poortinga-energieadvies.nl`** lezen, zodat die automatisch als lead in de isolatieplan-tool
komen. Nu gebeurt dat handmatig (mails uit Outlook slepen), bij tientallen mails per batch.

**Wat de toepassing doet:** één keer per klik de berichten van de laatste 30 dagen ophalen, daaruit de
berichten pakken die de term `AdviseurToegekend` bevatten en het JSON-blok uit de body lezen. Die term
staat in de **inhoud** (`"WijzigingsType"`); het onderwerp luidt "Contact met adviseur door accountid
…" en verschilt per aanmelding, dus daar valt niet op te filteren.
**Wat de toepassing niet doet:** niets markeren, verplaatsen, verwijderen of versturen. Alleen lezen.
De code staat in `dashboard/graph_mail.py` en is in te zien.

---

## 1. App-registratie aanmaken

Entra ID (Azure AD) → **App-registraties** → **Nieuwe registratie**

| Veld | Waarde |
|---|---|
| Naam | `Poortinga isolatieplan-tool (leads)` |
| Accounttypen | **Alleen accounts in deze organisatiemap** (single tenant) |
| Omleidings-URI | *leeg laten* — de toepassing is een achtergronddienst, geen webapplicatie |

Noteer na het aanmaken: **Toepassings-id (client)** en **Map-id (tenant)**.

## 2. Toestemming verlenen

**API-machtigingen** → **Machtiging toevoegen** → **Microsoft Graph** → **Toepassingsmachtigingen**
(let op: *toepassings*machtigingen, niet gedelegeerd — er is geen ingelogde gebruiker):

- `Mail.Read`

Daarna **Beheerderstoestemming verlenen** klikken. Zonder die stap geeft de toepassing een 403.

> `Mail.Read` als toepassingsmachtiging geeft in principe toegang tot álle postvakken. Stap 4 perkt
> dat in tot dit ene postvak. Voer stap 4 uit — zonder die policy is de machtiging breder dan nodig.

## 3. Clientgeheim aanmaken

**Certificaten en geheimen** → **Nieuw clientgeheim** → looptijd naar keuze (24 maanden is gangbaar).

De waarde is **eenmalig zichtbaar**. Geef die veilig door aan Renze (niet per gewone mail — bijvoorbeeld
via een wachtwoordmanager of een versleuteld kanaal). **Zet de vervaldatum in de agenda**: als het
geheim verloopt stopt het ophalen met een 401-melding.

## 4. Toegang beperken tot dit ene postvak (belangrijk)

In Exchange Online PowerShell:

```powershell
Connect-ExchangeOnline

New-ApplicationAccessPolicy `
  -AppId <TOEPASSINGS-ID uit stap 1> `
  -PolicyScopeGroupId info@poortinga-energieadvies.nl `
  -AccessRight RestrictAccess `
  -Description "Isolatieplan-tool mag uitsluitend het gedeelde info-postvak lezen"
```

Controleren:

```powershell
Test-ApplicationAccessPolicy -Identity info@poortinga-energieadvies.nl -AppId <TOEPASSINGS-ID>
```
Verwacht: `AccessCheckResult : Granted`. Test ook een willekeurig ander postvak; dat hoort
`Denied` te geven.

> De policy kan tot een uur nodig hebben om actief te worden.

## 5. Wat Renze nodig heeft

Drie waarden:

| Wat | Waar vandaan |
|---|---|
| Map-id (tenant) | stap 1 |
| Toepassings-id (client) | stap 1 |
| Clientgeheim | stap 3 |

Die komen in `config.json` van de toepassing (staat niet in versiebeheer, alleen op de server):

```json
"graph": {
  "tenant_id": "…",
  "client_id": "…",
  "client_secret": "…",
  "postvak": "info@poortinga-energieadvies.nl",
  "onderwerp": "AdviseurToegekend",
  "dagen": 30,
  "map": ""
}
```

`"map"` leeg = het hele postvak. Gaan de portalmails via een regel naar een submap, vul dan die
mapnaam in (bijvoorbeeld `"Nij Begun"`).

---

## Waar de toepassing draait

Op een eigen VPS bij TransIP (Nederland), achter HTTPS met tweefactor-login. De gegevens blijven
binnen de EU. Er worden geen mails opgeslagen: alleen naam, adres en contactgegevens uit het
JSON-blok gaan naar de leadlijst op die server.

## Foutmeldingen en wat ze betekenen

| Melding in de app | Oorzaak |
|---|---|
| 401, aanmelden geweigerd | tenant-id/client-id verkeerd, of het clientgeheim is verlopen |
| 403, toegang geweigerd | beheerderstoestemming niet verleend, of het postvak valt buiten de Application Access Policy |
| 404, postvak niet gevonden | adres in `"postvak"` klopt niet |
| "geen portal-mails gevonden" | verbinding is goed, maar geen berichten met die term in de periode |

## Alternatief als Graph niet gewenst is

Een doorstuurregel in Outlook naar een los postvak bij de webhoster (Cloud86), dat de toepassing via
IMAP met een gewoon wachtwoord leest. Minder netjes qua rechten, maar zonder app-registratie.
Zie `dashboard/mailbox.py`.
