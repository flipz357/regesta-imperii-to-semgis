import geohelpers as gh
import json

with open("resources/CANDIDATES_1.json") as f:
    C =json.load(f)

_, ii = gh.read_geo_names()

def maybe_extend_candidates(C,ii,strategy=None):
    if not strategy:
        return None
    for name in C:
        old = list(C[name])
        if name in ii and " " in name:
            a=2
        #    continue
        if " " in name:
            spl = name.split()
            for tok in spl:
                if tok in ii:
                    for cand in ii[tok]:
                        if cand not in C[name]:
                            C[name].append(cand)
        if name in ii and " " in name:
            print(name,C[name],old, name in ii and " " in name)

    return None

maybe_extend_candidates(C,ii,strategy="--")

