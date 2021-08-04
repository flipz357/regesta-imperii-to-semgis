import data_helpers as dh
import json
import numpy as np
import geohelpers as gh
from search import search, resolve_places_in_regests
import logging
import os
import distance as ds
import statistics
import argparse
from utils import int2loglevel
from constants import UNKNOWN


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-runid", nargs="?",default=0, type=str, 
            help="a run id to save the final output")

    parser.add_argument("-log_level", nargs="?",default=2, type=int, 
            help="logging level, 1: info, 2: debug, 0: ciritcal")

    parser.add_argument("-iterations", nargs="?",default=2, type=int, 
            help="number of bootstrap iterations")
    parser.add_argument("-unknown_strat", nargs="?",default="last", type=str, 
            help="unknown strat")

    parser.add_argument("--fresh_run", action='store_true',  
            help="if enabled, we do not look for memorized files" \
            "but run all processes anew (info: takes much time)")

    parser.add_argument("--fresh_candidates", action='store_true',  
            help="if enabled, we do not look for memorized" \
            "candidate location file but run this processes anew")

    #TODO implement
    parser.add_argument("--multi_processing", action='store_true', 
            help="use with caution, not properly implemented")

    parser.add_argument("--simple_candidate_extension", action='store_true', 
            help="if a name is stated with multiple tokens, look up direct hits in\
                    geo data-base of each single token and put into candidates")

    parser.add_argument("--dummy_run", action='store_true', 
            help="perform a dummy run with only a small set of" \
            "place names to be resolved")

    parser.add_argument("--interpolate_missing_text_place_predictions", action='store_true', 
            help="use majority vote in between iterations")

    parser.add_argument("-text_place_solver", nargs="?",default="stochastic", 
            help="method to resolve place-names in text")

    parser.add_argument("-entity_file_path", nargs="?",
            default="resources/ENTITIES.json", type=str, 
            help="path to store entities or load entities from")

    parser.add_argument("-place_candidate_file_path", nargs="?", 
            default="resources/CANDIDATES.json", type=str, 
            help="path to save place candidates or load candidates from")
    
    parser.add_argument("-RI_as_json_path", nargs="?", 
            default="../ri-data/RI.json", type=str, 
            help="path to load all regests")
    
    parser.add_argument("-entity_types", nargs="?", 
            default="../ri-data/entity_types.txt", type=str, 
            help="path to entity type list")

    parser.add_argument("-ner_method", nargs="?",default="spacy", type=str, 
            help="spacy or stanza")
    
    args = parser.parse_args()
    
    return args


if __name__ == '__main__':

    args = get_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s'
            ,level=int2loglevel(args.log_level))

    #load regests
    regests = dh.loadjson(args.RI_as_json_path)


    #sort by date 
    regests = list(sorted(regests,key=lambda r:r["date"][0]))

    if args.dummy_run:
        regests  = regests[10300:10500]
     

    entity_types = dh.load_entity_types(args.entity_types)

    #extract named entities associated with places from text
    text_nes = dh.extract_nes(regests, check_if_saved=args.fresh_run==False
            , clean=dh.clean_loc_string, save_path=args.entity_file_path
            , method=args.ner_method, entity_types=entity_types)

    text_nes_as_list = [text_nes[key] for key in [reg["uri"] for reg in regests]]
    text_names = []
    for elm in text_nes_as_list:
        tmp = []
        for ne_idx in elm["ents"]:
            place_name = elm["ents"][ne_idx].get("associated_with_loc")
            if place_name:
                tmp.append(place_name)
            else:
                tmp.append(elm["ents"][ne_idx].get("text"))
        text_names.append([dh.clean_loc_string(t) for t in tmp])

    additional_locs = [j for i in text_names for j in i]


    #clean and get unique place names
    names = [dh.clean_loc_string(regest["location"]) for regest in regests] 
    uniq_locations = list(set(names)) + list(set(additional_locs))
    uniq_locations = uniq_locations
    print(list(sorted(uniq_locations, key = len, reverse=True)))

    #load geodata
    geonames, ii = gh.read_geo_names()

    CANDIDATE_EXISTS=os.path.exists(args.place_candidate_file_path)

    #build candidate sets for every name in unique place names

    if CANDIDATE_EXISTS and not args.fresh_run and not args.fresh_candidates:
        
        logging.info("load saved place candidates from {}".format(
            args.place_candidate_file_path))
        
        with open(args.place_candidate_file_path,"r") as f:
            C=json.load(f)
        
        logging.info("loaded")
        

    elif not CANDIDATE_EXISTS or args.fresh_run or args.fresh_candidates:

        logging.info("retrieving candidates.... this may take a while...")
        C = gh.build_candidates(uniq_locations,data=geonames,ii=ii
                ,multiprocessing=args.multi_processing)
        logging.info("retrieving retrieved, stroing to {}".format(
            args.place_candidate_file_path))

        with open(args.place_candidate_file_path,"w") as f:
            f.write(json.dumps(C,indent=4,sort_keys=True))

    c_stats = statistics.candidate_stats(C)
    logging.info("candidate statistics\n\
                 unique place names: {}\n\
                 median places per name: {}\n\
                 avg. places per name: {}\
                 percentiles 50th 75th 90th \
                 95th 99th: {}".format(c_stats[0], 
                        c_stats[1],c_stats[2],c_stats[3]))

    if args.simple_candidate_extension:
        gh.maybe_extend_candidates(C, ii
                , strategy="single-token-match", entity_types=entity_types)
        c_stats = statistics.candidate_stats(C)
        logging.info("candidate statistics\n\
                     unique place names: {}\n\
                     median places per name: {}\n\
                     avg. places per name: {}\
                     percentiles 50th 75th 90th \
                     95th 99th: {}".format(c_stats[0], 
                            c_stats[1],c_stats[2],c_stats[3]))


    #intitalize query object
    QO = ds.QueryObject(geonames,costfun=ds.cost1)



    #if place name strings deviate too much, set them to UNKNWON

    exceptionfun = lambda x,y: any([tok for tok in x.split() if tok == y])
    
    input_names = gh.maybe_convert_dissimilar_placenames_to_unknown(names
            , C, geonames, lr=0.5, exceptionfun=exceptionfun)
    
    
    text_names = [gh.maybe_convert_dissimilar_placenames_to_unknown(ns
        , C, geonames, lr=0.5, exceptionfun=exceptionfun) for ns in text_names]
    

    #handle UNKNOWN names
    #in itinerary: default: set to last known name
    names_not_unknown = dh.unknown_handling(input_names, strat=args.unknown_strat)

    #in text: default: remove and interpolate later
    names_not_unknown_text = [list(set(dh.unknown_handling(tn, strat="remove"))) 
            for tn in text_names]


    places_in_regests = []
    path = []

    #start bootstrapping
    for iteration in range(args.iterations):
        logging.info("starting {}. global iteration".format(iteration))
        
        path = []

        
        #resolve itinerary
        path, cum_dist = search(names_not_unknown
                ,C
                ,QO
                ,init_memory=([0.0]*len(C[names_not_unknown[0]])
                    ,np.full( (len(C[names_not_unknown[0]]),1),-1).tolist()
                    ,C[names_not_unknown[0]])
                ,init_station=names[0]
                ,places_in_regests=places_in_regests
                )
        logging.info("solving emperor routes finished; \
                cumulative_distance {}".format(cum_dist))
        path = path[1:]
        path = [C[name][path[i]] for i,name in enumerate(names_not_unknown)]
        
        places_in_regests, avg_cost = resolve_places_in_regests(
                names_not_unknown_text,C,QO,path,method=args.text_place_solver)
        logging.info("solving places in text finished; method={}, \
                avg cost={}".format(args.text_place_solver,avg_cost))

    ## checks and creating final output files
    assert len(path) == len(names_not_unknown)
    assert len(places_in_regests) == len(path)
    
    place_predictions = {}
    text_place_predictions = {}
    for i in range(len(path)):
        uri = regests[i]["uri"]
        place_predictions[uri] = {"used name":input_names[i]
                ,"prediction:":gh.id_to_info_dict(path[i],geonames)}
        text_place_predictions[uri] = {}
        for idx in text_nes[uri]["ents"]:
            if "associated_with_loc" in text_nes[uri]["ents"][idx]:
                tmploc = dh.clean_loc_string(
                        text_nes[uri]["ents"][idx]["associated_with_loc"])
            else:
                tmploc = dh.clean_loc_string(text_nes[uri]["ents"][idx]["text"])
            if tmploc in names_not_unknown_text[i]:
                k = places_in_regests[i][names_not_unknown_text[i].index(tmploc)]
                text_nes[uri]["ents"][idx]["prediction"] = gh.id_to_info_dict(k
                        , geonames)
                text_nes[uri]["ents"][idx]["used_name"] = tmploc
            else:
                text_nes[uri]["ents"][idx]["prediction"] = UNKNOWN
                text_nes[uri]["ents"][idx]["used_name"] = tmploc

        if args.interpolate_missing_text_place_predictions:
            
            allidxs_in_regest_places = [
                    text_nes[uri]["ents"][idx]["prediction"]["geonameid"] 
                    for idx in text_nes[uri]["ents"] 
                    if text_nes[uri]["ents"][idx]["prediction"] != UNKNOWN
                    ]
            
            if not allidxs_in_regest_places:
                continue
            else:
                lat, lng = ds.get_center(allidxs_in_regest_places, geonames)
                for idx in text_nes[uri]["ents"]:
                    if text_nes[uri]["ents"][idx]["prediction"] == UNKNOWN:
                        dummy = gh.dummy_info_dict(lat, lng, allidxs_in_regest_places)
                        text_nes[uri]["ents"][idx]["prediction"] = dummy

        if i % 10 == 0:
            logging.debug("place_predictions saved {}/{}".format(i,len(path)))


    logging.info("place prediction finished, storing entity place predictions \
            to {} and emperor itineraries to {}".format(
                "predictions/charter_locations_{}.json".format(args.runid),
                "predictions/NE_locations_{}.json".format(args.runid)))

    # write files
    with open("predictions/charter_locations_{}.json".format(args.runid),"w") as f:
        f.write(json.dumps(place_predictions,indent=4))
    with open("predictions/NE_locations_{}.json".format(args.runid),"w") as f:
        f.write(json.dumps(text_nes,indent=4))
    logging.info("place prediction finished, outputfiles written, program exiting...")

