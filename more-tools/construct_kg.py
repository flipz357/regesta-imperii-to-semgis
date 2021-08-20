import json
import argparse
import datetime
from collections import Counter, defaultdict
import Levenshtein

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-itinerary_file", required=True, type=str,
                            help="path to itinerary predictions with centers added")
    
    parser.add_argument("-ner_loc_file", required=True, type=str,
                            help="path to NE predictions with centers added")

    parser.add_argument("-emperor", type=str
                        ,help="e.g. Friedrich II.")
    
    parser.add_argument("-min_ent_count", type=int, default=2
                        ,help="5")
    
    parser.add_argument("--only_show_possible_emperors", action = "store_true",
                        help="shows all possible emperors")

    args = parser.parse_args()
    
    return args


def create_graph(RI, it_dic, ent_dic, min_ent_count = 2, emp = "Friedrich II."):
    triples = []
    
    # we construct an entity count dictionary first to filter infrequent ones later
    ent_count = defaultdict(int)
    for reg in RI:
        uri = reg["uri"]
        if reg["issuer"] != emp:
            continue
        for entidx in ent_dic[uri]["ents"]:
            ent_count[ent_dic[uri]["ents"][entidx]["text"]] += 1
    done_ents = {}

    #we iterate over the regests
    for reg in RI:
        uri = reg["uri"]
        if reg["issuer"] != emp:
            continue

        # we insert basic triples such as issuer, date, location name
        triples.append([uri,":issuer", reg["issuer"]])
        triples.append([uri,":date", reg["date"][0]])
        triples.append([uri,":locname", reg["location"]])

        # we insert the geo prediction for the lcoation name
        triples.append([uri,":locpred"
            , it_dic[uri]["prediction-center"]["latitude"] 
            + "," +it_dic[uri]["prediction-center"]["longitude"]])
        
        # we iterate over the entities in a regest
        for entidx in ent_dic[uri]["ents"]:
            if ent_count[ent_dic[uri]["ents"][entidx]["text"]] < min_ent_count:
                continue

            #we retrieve the dependency path to the root
            rels = ["NA"]+ent_dic[uri]["ents"][entidx]["heads"]

            # we add the edge label to the next head and the next head
            triple = [uri, rels[-1], ent_dic[uri]["ents"][entidx]["text"]]
            triples.append(triple) 
            
            
            if ent_count[ent_dic[uri]["ents"][entidx]["text"]] in done_ents:
                continue
            else:
                if not "prediction-center" in ent_dic[uri]["ents"][entidx]:
                    continue

                # we add the predicted place id of the entitiy
                triple = [ent_dic[uri]["ents"][entidx]["text"]
                        , ":locpred"
                        , ent_dic[uri]["ents"][entidx]["prediction-center"]["latitude"]
                        +","+ent_dic[uri]["ents"][entidx]["prediction-center"]["longitude"]]
                triples.append(triple)

                # we add the label of the named entitiy, i.e. PER or LOC
                triples.append([ent_dic[uri]["ents"][entidx]["text"]
                    ,":label"
                    ,ent_dic[uri]["ents"][entidx]["label"]])
                done_ents[ent_dic[uri]["ents"][entidx]["text"]] = 1
    return triples

        
def loadj(p):
    with open(p,"r") as f:
        return json.load(f)

    
if __name__ == "__main__":
    args = get_args()
    
    # load the regests
    RI = loadj("../ri-data/RI.json")
    
    # load the predicted itineraries
    it_dic = loadj(args.itinerary_file)

    # load the entity dict
    ent_dic = loadj(args.ner_loc_file)

    # get the graph
    G = create_graph(RI, it_dic, ent_dic, args.min_ent_count, args.emperor)
    
    #store the graph
    with open("knowledge_graphs/graph-issuer:{}-mincount:{}.tsv".format(args.emperor, args.min_ent_count),"w") as f:
        f.write("\n".join(["\t".join(t) for t in G]))
    
