"""
Rip alle leesbare strings (UTF-16LE + ASCII) uit de native EPA-exe. De Nederlandse
model-/keuzelijst-teksten (bv. 'Dak isol. onbekend', 'TripleHR glas', 'A.1 Standaard',
'Vloer thermokussen') blijken letterlijk als UTF-16 in EPA_NTA8800.exe te staan. Dit is
de OFFLINE, token-vrije bron voor ALLE dropdown-opties (alle paden), herhaalbaar bij een
VABI-update.

    python vabi/extract_strings.py --exe "C:/Program Files (x86)/Vabi/EPA (NTA8800)/EPA_NTA8800.exe"

Schrijft:
  vabi/refs/exe_strings_all.txt      - alle unieke strings (ruwe bron)
  Filtering/clustering naar enum-lijsten doet vabi/build_enum_catalog.py (aparte stap).
"""
import os, re, argparse

DEFAULT_EXE = r"C:/Program Files (x86)/Vabi/EPA (NTA8800)/EPA_NTA8800.exe"
HERE = os.path.dirname(os.path.abspath(__file__))


def rip_utf16(data, min_len=3):
    """Aaneengesloten reeksen printbare UTF-16LE-tekens."""
    out, i, n = [], 0, len(data)
    cur = []
    while i + 1 < n:
        lo, hi = data[i], data[i + 1]
        if hi == 0 and (32 <= lo < 127 or lo in (9,)):
            cur.append(chr(lo)); i += 2; continue
        # ook niet-ASCII latin (à, ë, ï, é ...) in UTF-16: hi==0 al gedekt; sta 0x00A0-0x024F toe
        cp = lo | (hi << 8)
        if 0x00A0 <= cp <= 0x024F:
            cur.append(chr(cp)); i += 2; continue
        if len(cur) >= min_len:
            out.append("".join(cur))
        cur = []; i += 2
    if len(cur) >= min_len:
        out.append("".join(cur))
    return out


def rip_ascii(data, min_len=4):
    return [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--out", default=os.path.join(HERE, "refs", "exe_strings_all.txt"))
    a = ap.parse_args()
    data = open(a.exe, "rb").read()
    s = set(rip_utf16(data)) | set(rip_ascii(data))
    s = {x.strip() for x in s if x.strip()}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        for x in sorted(s):
            fh.write(x + "\n")
    print("exe: %s (%.1f MB)" % (a.exe, len(data) / 1e6))
    print("unieke strings: %d -> %s" % (len(s), a.out))


if __name__ == "__main__":
    main()
