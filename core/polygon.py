"""Gedeelde, dependencyvrije validatie voor eenvoudige 2D-polygonen."""

EPS = 1e-10


def oppervlakte(punten):
    return abs(sum(punten[i][0] * punten[(i + 1) % len(punten)][1]
                   - punten[(i + 1) % len(punten)][0] * punten[i][1]
                   for i in range(len(punten))) / 2.0)


def _orientatie(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _op_segment(a, b, p):
    return (abs(_orientatie(a, b, p)) <= EPS
            and min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS
            and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS)


def _segmenten_kruisen(a, b, c, d):
    o1, o2, o3, o4 = (_orientatie(a, b, c), _orientatie(a, b, d),
                      _orientatie(c, d, a), _orientatie(c, d, b))
    if ((o1 > EPS and o2 < -EPS) or (o1 < -EPS and o2 > EPS)) and \
       ((o3 > EPS and o4 < -EPS) or (o3 < -EPS and o4 > EPS)):
        return True
    return ((abs(o1) <= EPS and _op_segment(a, b, c))
            or (abs(o2) <= EPS and _op_segment(a, b, d))
            or (abs(o3) <= EPS and _op_segment(c, d, a))
            or (abs(o4) <= EPS and _op_segment(c, d, b)))


def zelfsnijdend(punten):
    n = len(punten)
    for i in range(n):
        vorig, huidig, volgend = punten[i - 1], punten[i], punten[(i + 1) % n]
        if abs(_orientatie(vorig, huidig, volgend)) <= EPS and _op_segment(vorig, huidig, volgend):
            return True
    for i in range(n):
        a, b = punten[i], punten[(i + 1) % n]
        for j in range(i + 1, n):
            if j in (i, (i + 1) % n) or (j + 1) % n in (i, (i + 1) % n):
                continue
            if _segmenten_kruisen(a, b, punten[j], punten[(j + 1) % n]):
                return True
    return False
