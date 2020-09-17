import data_helpers as dh
import json
from collections import defaultdict, Counter
import argparse
from voter import Voter,use_id_voter_simple_on_list, use_dist_voter_simple_on_list
from constants import UNKNOWN, UNKNOWN_ID


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-itinerary_file", required=True, type=str,
                    help="path to itinerary")

    parser.add_argument("-ner_place_file", required=True, type=str,
                    help="path to itinerary")

    parser.add_argument("-solver_option", nargs="?",default="id_voter", type=str,
                    help="id_voter")

    parser.add_argument("--solve_jointly", action="store_true",
                    help="if yes then learn solver on both inputs, otherwise \
                            separately")

    args=parser.parse_args()

    return args


if __name__ == '__main__':
    
    args = get_args()

    #load itinerary preds
    its = dh.loadjson(args.itinerary_file)

    #load Entitiy location preds
    ners = dh.loadjson(args.ner_place_file)
    #dh._maybe_convert_ent_dict_to_actual_format(ners)


    keys = list(sorted(its.keys()))

    #get geoname ID preds for itineraries
    predids = [its[key]["prediction:"]["geonameid"] for key in keys]
    unames = [its[key]["used name"] for key in keys]
    prednames = [its[key]["prediction:"]["asciiname"] for key in keys]

    id_pred = {its[key]["prediction:"]["geonameid"]:its[key]["prediction:"] for key in keys}

    for i,elm in enumerate(unames):
        if elm == UNKNOWN:
            predids[i] = UNKNOWN_ID



    #get geoname ID preds for ents
    predids_ner = []
    unames_ner = []
    prednames_ner = []

    for key in keys:
        for idx in ners[key]["ents"]:
            if ners[key]["ents"][idx]["associated_with_loc"] == UNKNOWN:
                continue
            if ners[key]["ents"][idx]["prediction"] == UNKNOWN or ners[key]["ents"][idx]["used_name"] == UNKNOWN:
                continue
            
            geoi = ners[key]["ents"][idx]["prediction"]["geonameid"]
            if "INTERPOLATION" in geoi:
                continue
            un = ners[key]["ents"][idx]["used_name"]
            if un == UNKNOWN:
                continue
            an = ners[key]["ents"][idx]["prediction"]["asciiname"]
            predids_ner.append(geoi)
            unames_ner.append(un)
            prednames_ner.append(an)
            if geoi not in id_pred:
                id_pred[geoi] = ners[key]["ents"][idx]["prediction"]

    if args.solve_jointly:
        #compute centers jointly
        spli = len(predids)
        predids = use_id_voter_simple_on_list(predids + predids_ner, unames + unames_ner)
        predids_ner = list(predids[spli:])
        predids = predids[:spli]
    else:
        #or separately
        predids = use_id_voter_simple_on_list(predids,unames)
        predids_ner = use_id_voter_simple_on_list(predids_ner, unames_ner)


    #add output for itineraries
    for i,key in enumerate(keys):
        its[key]["prediction-center"] = id_pred[predids[i]]

    #add output for ners
    c = 0
    for i,key in enumerate(keys):
        for j,idx in enumerate(ners[key]["ents"]):
            if ners[key]["ents"][idx]["associated_with_loc"] == UNKNOWN:
                continue
            if ners[key]["ents"][idx]["prediction"] == UNKNOWN or ners[key]["ents"][idx]["used_name"] == UNKNOWN:
                continue
            
            geoi = ners[key]["ents"][idx]["prediction"]["geonameid"]
            if "INTERPOLATION" in geoi:
                continue
            un = ners[key]["ents"][idx]["used_name"]
            if un == UNKNOWN:
                continue
            ners[key]["ents"][idx]["prediction-center"] = id_pred[predids_ner[c]]
            c+=1

    #write outpus
    with open(args.itinerary_file.replace(".json","")+"-_centers_added.json", "w") as f:
        f.write(json.dumps(its, sort_keys=True, indent=4))
    with open(args.ner_place_file.replace(".json","")+"-_centers_added.json", "w") as f:
        f.write(json.dumps(ners, sort_keys=True, indent=4))
