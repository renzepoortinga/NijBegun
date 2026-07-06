"""
Beveiliging voor de gehoste webapp (nijbegun.poortinga-energieadvies.nl) — M29 Bijlage 1 punt 25-27:
EU-opslag, geen datadeling zonder toestemming, MINIMAAL MFA voor adviseurs.

Alles pure stdlib (geen extra dependencies):
- Wachtwoord-hashing:  PBKDF2-HMAC-SHA256 (260k iteraties, per-hash salt)
- MFA:                 TOTP (RFC 6238, zoals Google/Microsoft Authenticator; 30s-venster)
- Rate-limiting:       max 5 mislukte pogingen per kwartier per IP (in-memory)

Instellen (eenmalig, lokaal):
    python dashboard/security.py --setup
-> vraagt een wachtwoord, genereert een TOTP-secret + otpauth-URI (scan met je authenticator-app)
   en schrijft pw_hash + totp_secret in config.json onder "dashboard".
Zonder pw_hash in config.json blijft de app in LOKALE modus (plain wachtwoord, geen MFA) werken.
"""
import base64, hashlib, hmac, json, os, secrets, struct, time

ITERATIES = 260_000
MAX_POGINGEN = 5
VENSTER_S = 15 * 60
_pogingen = {}          # ip -> [timestamps van mislukte pogingen]


# ---------------- wachtwoord ----------------
def hash_password(pw, salt=None, iteraties=ITERATIES):
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt.encode("ascii"), iteraties)
    return "pbkdf2$%d$%s$%s" % (iteraties, salt, dk.hex())


def check_password(pw, opgeslagen):
    try:
        _, it, salt, _ = opgeslagen.split("$")
        return hmac.compare_digest(hash_password(pw, salt, int(it)), opgeslagen)
    except Exception:
        return False


# ---------------- TOTP (RFC 6238) ----------------
def nieuw_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret_b32, t=None, stap=30, cijfers=6):
    s = secret_b32.strip().replace(" ", "").upper()
    key = base64.b32decode(s + "=" * ((8 - len(s) % 8) % 8))
    teller = int((time.time() if t is None else t) // stap)
    h = hmac.new(key, struct.pack(">Q", teller), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** cijfers)
    return str(code).zfill(cijfers)


def check_totp(secret_b32, code, venster=1, t=None):
    code = (code or "").strip().replace(" ", "")
    if not (secret_b32 and code):
        return False
    nu = time.time() if t is None else t
    return any(hmac.compare_digest(totp_code(secret_b32, nu + i * 30), code)
               for i in range(-venster, venster + 1))


def otpauth_uri(secret_b32, account="adviseur", issuer="NijBegun-Poortinga"):
    return ("otpauth://totp/%s:%s?secret=%s&issuer=%s&digits=6&period=30"
            % (issuer, account, secret_b32, issuer))


# ---------------- rate-limiting ----------------
def geblokkeerd(ip):
    nu = time.time()
    _pogingen[ip] = [t for t in _pogingen.get(ip, []) if nu - t < VENSTER_S]
    return len(_pogingen[ip]) >= MAX_POGINGEN


def poging_mislukt(ip):
    _pogingen.setdefault(ip, []).append(time.time())


def poging_gelukt(ip):
    _pogingen.pop(ip, None)


# ---------------- gecombineerde login-check ----------------
def login_check(dash_cfg, wachtwoord, code, ip, fallback_pw=""):
    """-> (ok, foutmelding). Hash+MFA indien geconfigureerd; anders lokale modus (plain wachtwoord)."""
    if geblokkeerd(ip):
        return False, "Te veel mislukte pogingen — probeer het over een kwartier opnieuw."
    pw_hash = (dash_cfg or {}).get("pw_hash", "")
    if pw_hash:
        ok = check_password(wachtwoord or "", pw_hash)
        secret = (dash_cfg or {}).get("totp_secret", "")
        if ok and secret:
            ok = check_totp(secret, code)
            if not ok:
                poging_mislukt(ip)
                return False, "Wachtwoord klopt, maar de 6-cijferige code niet (authenticator-app)."
    else:
        ok = (wachtwoord or "") == fallback_pw
    if ok:
        poging_gelukt(ip)
        return True, ""
    poging_mislukt(ip)
    return False, "Onjuist wachtwoord."


# ---------------- setup-CLI ----------------
def main():
    import argparse, getpass
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="Webapp-beveiliging instellen (wachtwoord-hash + MFA)")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--config", default=os.path.join(root, "config.json"))
    a = ap.parse_args()
    if not a.setup:
        ap.print_help(); return
    cfg = {}
    if os.path.exists(a.config):
        cfg = json.load(open(a.config, encoding="utf-8"))
    pw = getpass.getpass("Nieuw dashboard-wachtwoord: ")
    if len(pw) < 10:
        print("FOUT: gebruik minimaal 10 tekens."); return
    if getpass.getpass("Nogmaals: ") != pw:
        print("FOUT: wachtwoorden verschillen."); return
    secret = nieuw_totp_secret()
    d = cfg.setdefault("dashboard", {})
    d["pw_hash"] = hash_password(pw)
    d["totp_secret"] = secret
    d.pop("wachtwoord", None)               # oude plain wachtwoord opruimen
    json.dump(cfg, open(a.config, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nOK — pw_hash + totp_secret in %s gezet (plain wachtwoord verwijderd)." % a.config)
    print("\nMFA instellen: voeg dit secret toe in je authenticator-app (Google/Microsoft Authenticator):")
    print("  Secret:  %s" % secret)
    print("  Of URI:  %s" % otpauth_uri(secret))
    print("\nHuidige code (ter controle): %s" % totp_code(secret))
    print("\nHost je op Render/Railway (PaaS)? Zet daar deze omgevingsvariabelen (Environment):")
    print("  NIJBEGUN_PW_HASH     = %s" % d["pw_hash"])
    print("  NIJBEGUN_TOTP_SECRET = %s" % secret)


if __name__ == "__main__":
    main()
