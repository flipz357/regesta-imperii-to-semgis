import json
import argparse
import datetime
from collections import Counter, defaultdict
import Levenshtein
#from constants import UNKNOW

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-itinerary_file", required=True, type=str,
                            help="path to itinerary predictions with centers added")

    parser.add_argument("-emperor", type=str
                        ,help="e.g. Friedrich II.")
    
    parser.add_argument("--only_show_possible_emperors", action = "store_true",
                        help="shows all possible emperors")

    args = parser.parse_args()
    
    return args


def date_to_ms(date="2000-01-31"):
    ds = [int(x) for x in date.split("-")]
    try:
        return datetime.datetime(ds[0],ds[1],ds[2]).timestamp() * 1000
    except ValueError:
        return None


def create(p, emp = "Friedrich II.", deeds = False):
    with open(p) as f:
        dat = json.load(f)

    with open("../ri-data/RI.json") as f:
        ri = json.load(f)
        ridict = {reg["uri"]:reg for reg in ri}
    if deeds:
        with open(p.replace("charter","NE")) as f:
            tmp = json.load(f)
        serialized_docs = {key:tmp[key]["serialization of preprocessed doc"] for key in tmp}
    dic = {"locations": [], "deeds":[]}
    print(Counter([reg["issuer"] for reg in ri]))
    allowed = {reg["uri"]:1 for reg in ri if reg["issuer"] == emp}
    dat = {key:dat[key] for key in dat if key in allowed}
    
    for key in dat:
        lng = float(dat[key]["prediction-center"]["longitude"])*1e7
        lat = float(dat[key]["prediction-center"]["latitude"])*1e7
        date = ridict[key]["date"][1]
        date = date_to_ms(date)
        if not date:
            continue
        tmp = {"timestampMs":date, "latitudeE7":lat, "longitudeE7":lng}
        dic["locations"].append(tmp)
        if deeds:
            toks = serialized_docs.split("#tok:::")[1].split("\n")[0].split()
            deps = serialized_docs.split("#dep:::")[1].split("\n")[0].split()
            deed = ""
            if "ROOT" in deps:
                i = deps.index("ROOT")
                deed = toks[i]
            dic["deeds"].append(deed)

            
    return dic 

def create_from_content(p, emp = "Friedrich II.", mincount = 2):
    with open(p) as f:
        dat = json.load(f)

    with open("../ri-data/RI.json") as f:
        ri = json.load(f)
        ridict = {reg["uri"]:reg for reg in ri}
    dic = {"locations": [], "ents": []}
    allowed = {reg["uri"]:1 for reg in ri if reg["issuer"] == emp}
    dat = {key:dat[key] for key in dat if key in allowed}
    text = []
    year_deeds = defaultdict(list)
    deeds = []
    for key in dat:
        deed = ""
        deps = dat[key]["serialization of preprocessed doc"].split("#dep:::")[1].split("\n")[0].split()
        toks = dat[key]["serialization of preprocessed doc"].split("#tok:::")[1].split("\n")[0].split()
        deed = ""
        if "ROOT" in deps:
            i = deps.index("ROOT")
            deed = toks[i]
        for i,idx in enumerate(dat[key]["ents"]):
            if dat[key]["ents"][idx]["text"] == "UNKNOWN":
                continue
            if dat[key]["ents"][idx]["prediction"] == "UNKNOWN":
                continue
            if "INTERPOLATION" in dat[key]["ents"][idx]["prediction"]["asciiname"]:
                continue
            lng = float(dat[key]["ents"][idx]["prediction-center"]["longitude"])*1e7
            lat = float(dat[key]["ents"][idx]["prediction-center"]["latitude"])*1e7
            if Levenshtein.ratio(dat[key]["ents"][idx]["text"].lower(),dat[key]["ents"][idx]["prediction-center"]["asciiname"].lower()) < 0.9:
                continue
            date = ridict[key]["date"][1]
            year = date.split("-")[0]
            date = date_to_ms(date)
            if not date:
                continue
            if dat[key]["ents"][idx]["text"].lower() in ["stadt", "reich"]:
                continue
            tmp = {"timestampMs":date, "latitudeE7":lat, "longitudeE7":lng}
            toks = dat[key]["serialization of preprocessed doc"].split("#tok:::")[1].split("\n")[0]
            try:
                fsi = toks.index(" .")
                txi = toks.index(dat[key]["ents"][idx]["text"])
            except ValueError:
                continue
            if fsi < txi:
                continue
            dic["locations"].append(tmp)
            dic["ents"].append(dat[key]["ents"][idx]["text"])
            text.append(dat[key]["ents"][idx]["text"])
            year_deeds[year].append(deed)
            deeds.append(deed)
            if i >  3:
                break
    print (Counter(text).most_common(40))
    print(Counter(deeds).most_common(5))
    return dic 

    
    
if __name__ == "__main__":
    args = get_args()
    if "NE" in args.itinerary_file:
        charter_or_content_loc = "NE"
        dic = create_from_content(args.itinerary_file, args.emperor)
    else:
        charter_or_content_loc = "charter"
        dic = create(args.itinerary_file, args.emperor)

    with open("googlemaphistory/googlemaphistory-{}-{}.json".format(args.emperor, charter_or_content_loc).replace(" ","_"),"w") as f:
        f.write(json.dumps(dic))

