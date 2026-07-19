"""
Een geheim in config.json zetten zonder met de hand JSON te bewerken.

Waarom dit bestaat: clientgeheimen van Entra VERLOPEN (meestal na 12-24 maanden). Dan moet je een
nieuw geheim aanmaken en hier invoeren. Handmatig knippen en plakken in JSON gaat één keer per twee
jaar mis op een ontbrekende komma, en dan start de webapp niet meer.

Gebruik (vraagt het geheim, toont het niet op het scherm):

    python dashboard/zet_geheim.py graph.client_secret

Of, als je het al ergens hebt staan:

    python dashboard/zet_geheim.py graph.client_secret --waarde "xxxx"

Er wordt altijd eerst een backup gemaakt (config.json.bak) en na afloop gecontroleerd of het
bestand nog geldige JSON is. Het geheim wordt NIET afgedrukt en niet gelogd.
"""
import os, sys, json, shutil, getpass, argparse, collections

HIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.dirname(HIER), "config.json")


def zet(pad, waarde, config=CONFIG):
    """pad = 'blok.veld' (bv. graph.client_secret). -> melding voor de gebruiker."""
    if "." not in pad:
        return "Geef het veld op als blok.veld, bijvoorbeeld graph.client_secret"
    blok, veld = pad.split(".", 1)
    if not os.path.isfile(config):
        return "config.json niet gevonden op %s" % config
    with open(config, encoding="utf-8") as fh:
        d = json.load(fh, object_pairs_hook=collections.OrderedDict)
    shutil.copyfile(config, config + ".bak")
    d.setdefault(blok, collections.OrderedDict())[veld] = waarde
    with open(config, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
    with open(config, encoding="utf-8") as fh:           # controle: nog steeds geldige JSON?
        json.load(fh)
    return "%s gezet (%d tekens). Backup: config.json.bak" % (pad, len(waarde))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("veld", help="blok.veld, bv. graph.client_secret")
    p.add_argument("--waarde", help="de waarde; weglaten = veilig invoeren zonder dat het zichtbaar is")
    a = p.parse_args()
    waarde = a.waarde
    if waarde is None:
        waarde = getpass.getpass("Waarde voor %s (invoer blijft onzichtbaar): " % a.veld)
    waarde = (waarde or "").strip()
    if not waarde:
        print("Niets ingevoerd — config.json ongewijzigd.")
        return 1
    print(zet(a.veld, waarde))
    return 0


if __name__ == "__main__":
    sys.exit(main())
