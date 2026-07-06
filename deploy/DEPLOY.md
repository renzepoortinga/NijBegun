# Deploy — nijbegun.poortinga-energieadvies.nl

De webapp gehost op je eigen subdomein, AVG/M29-conform (EU-opslag, HTTPS, **MFA verplicht** in
productie — Bijlage 1 punt 25–27). Je hoofdwebsite blijft ongemoeid; alleen een subdomein-record erbij.

## Wat je nodig hebt (eenmalig, ±30 min)
1. **Een EU-servertje** — bv. Hetzner CX22 (~€4/mnd, Falkenstein/Neurenberg = EU) of TransIP Blade VPS (NL).
   Kies Ubuntu 24.04. Noteer het IP-adres.
2. **DNS-record** — in het beheerpaneel van poortinga-energieadvies.nl (waar je domein loopt):
   voeg een **A-record** toe: naam `nijbegun`, waarde = het server-IP, TTL standaard.
3. **Beveiliging instellen** (lokaal, vóór het uploaden):
       python dashboard/security.py --setup
   → kies een sterk wachtwoord (≥10 tekens), scan het TOTP-secret in je **authenticator-app**
   (Google/Microsoft Authenticator). Dit zet `pw_hash` + `totp_secret` in config.json en
   verwijdert het platte wachtwoord. **Zonder MFA weigert de productie-modus te starten.**

## De server inrichten (via ssh, of ik doe het met je mee via de browser-console)
    apt update && apt install -y docker.io docker-compose-v2 git
    git clone https://github.com/renzepoortinga/NijBegun.git /opt/nijbegun
    cd /opt/nijbegun
    # config.json (met pw_hash/totp_secret + adviseur-gegevens) veilig overzetten, bv.:
    #   scp config.json root@SERVER-IP:/opt/nijbegun/config.json     (vanaf je eigen PC)
    docker compose -f deploy/docker-compose.yml up -d --build

Caddy haalt automatisch het HTTPS-certificaat op (Let's Encrypt) zodra het DNS-record doorwerkt.
Daarna: https://nijbegun.poortinga-energieadvies.nl → inloggen met wachtwoord + MFA-code.

## Updaten (nieuwe versie uitrollen)
    cd /opt/nijbegun && git pull && docker compose -f deploy/docker-compose.yml up -d --build

## Backups (belangrijk — projectdata + leads staan in out/)
    # dagelijkse cron op de server, bv.:
    tar czf /root/backup-nijbegun-$(date +%F).tar.gz /opt/nijbegun/out /opt/nijbegun/config.json
Bewaar kopieën off-server (bv. terugsyncen naar je eigen PC). `out/` bevat persoonsgegevens →
zelfde AVG-zorg als lokaal.

## AVG / M29-checklist
- [x] EU-datacenter gekozen (Hetzner DE / TransIP NL)                    (M29 punt 25)
- [x] Geen datadeling zonder toestemming — data blijft op jouw server    (M29 punt 26)
- [x] MFA verplicht in productie (TOTP)                                  (M29 punt 27)
- [x] HTTPS (Caddy/Let's Encrypt) + HSTS + security-headers + rate-limit + CSRF-origin-check
- [ ] Verwerkersovereenkomst met de hoster afsluiten (Hetzner/TransIP hebben standaard-DPA's)
- [ ] Backup-cron aanzetten + 1x restore testen

## Wat bewust NIET meeverhuist
- **Vabi EPA-W blijft op je Windows-PC** (desktop-software): je downloadt de VABI-import uit de
  webapp, rekent lokaal, en uploadt de export terug — precies zoals nu.
- De MagicPlan-CSV upload je gewoon in de webapp (werkt vanaf elke plek, ook op de bouwplaats).
