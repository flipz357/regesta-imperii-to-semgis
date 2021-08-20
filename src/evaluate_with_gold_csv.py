import numpy as np
import json
from geopy.distance import vincenty
import data_helpers as dh
import sys
from sklearn.metrics import mean_squared_error
from scipy.stats import pearsonr
import argparse
from data_helpers import load_manual
import logging
from constants import UNKNOWN

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-itinerary_file", required=True, type=str,
                            help="path to itinerary predictions with centers added")

    parser.add_argument("-gold_csv_path", required=False, type=str, 
                            default = "../ri-data/ortsliste_ri_neu.txt",
                            help="path to gold csv")
    
    parser.add_argument("-RI_as_json_path", required=False, type=str,
                            default = "../ri-data/RI.json",
                            help="path to RI json")
    
    parser.add_argument("-level", required=True, type=str,
                            choices = ["event", "event-center", "macro"],
                            help="event; event-center; macro")

    parser.add_argument("-human_anno_type", required=False, type=str,
                            choices = ["geonameids","coordinates"], 
                            default = "coordinates",
                            help="select whether we use the human geoname\
			     ids or directly the human coordinates for eval")
    
    parser.add_argument("--times", action="store_true"
                        ,help="print km error over times")

    
    args = parser.parse_args()


    return args


def create_gold_uri_loc_mapping(ridict, gold_csv_path, opt="coordinates"):
    if opt == "coordinates":
        manualdict = dh.load_manual(gold_csv_path)
        return create_gold_uri_loc_mapping_by_coordinates(ridict, manualdict)
    elif opt == "geonameids":
        manualdict = dh.load_manual_geonamesid(gold_csv_path)
        return create_gold_uri_loc_mapping_by_geoname_id(ridict, manualdict)


def add2dict(dic, uri, lat="NA", lng="NA", name="NA", is_confident="NA"):

    dic[uri]["lat-manual"] = lat
    dic[uri]["lng-manual"] = lng
    dic[uri]["placenamepred-manual"] = name
    dic[uri]["manual-secure"] = is_confident

    return None


def create_gold_uri_loc_mapping_by_coordinates(ridict, manualdict):
    gold = {}
    man = manualdict
    for uri,elm in ridict.items():
        gold[uri] = {}
        e = elm["location"]
        if e in man:
            add2dict(gold, uri, man[e][1], man[e][2], man[e][0], man[e][3])
            #gold[uri]["lat-manual"] = man[e][1]
            #gold[uri]["placenamepred-manual"] = man[e][0]
            #gold[uri]["lng-manual"] = man[e][2]
            #gold[uri]["manual-secure"]=man[e][3]
        else:
            add2dict(gold, uri)
            #gold[uri]["lat-manual"] = "NA"
            #gold[uri]["placenamepred-manual"] = "NA"
            #gold[uri]["lng-manual"] = "NA"
            #gold[uri]["manual-secure"] = "NA"
        gold[uri]["given name"] = e
        gold[uri]["date"] = ridict[uri]["date"][0]
    return gold


def create_gold_uri_loc_mapping_by_geoname_id(ridict,manualdict):
    gold = {}
    man = manualdict
    import geohelpers as gh
    geonames, _ = gh.read_geo_names()
    for uri,elm in ridict.items():
        gold[uri] = {}
        e = elm["location"]
        if e in man and man[e] in geonames:
            add2dict(gold, uri, geonames[man[e]]["latitude"], geonames[man[e]]["longitude"], man[e][0], man[e][3])
            #gold[uri]["lat-manual"] = geonames[man[e]]["latitude"]
            #gold[uri]["lng-manual"] = geonames[man[e]]["longitude"]
            #gold[uri]["placenamepred-manual"] = man[e][0]
            #gold[uri]["manual-secure"]=man[e][3]
        else:
            add2dict(gold, uri)
            #gold[uri]["lat-manual"] = "NA"
            #gold[uri]["placenamepred-manual"] = "NA"
            #gold[uri]["lng-manual"] = "NA"
            #gold[uri]["manual-secure"] = "NA"
        gold[uri]["given name"] = e
        gold[uri]["date"] = ridict[uri]["date"][0]
    return gold


def get_data(pred_uri_loc_mapping
        , gold_uri_loc_mapping
        , level="event"
        , text_places=False
        , macrotimes = False):
    
    this_preds = pred_uri_loc_mapping
    this = []
    o19 = []
    gold = []
    done ={}
    idx_uri  = {}
    idx=0
    # function for rounding to bins of 25 years in case of macro times
    rd = lambda x: int(round(float(x)/25)*25)
    years = []
    if not text_places:
        for uri in gold_uri_loc_mapping:
            if uri not in this_preds:
                logging.warning("found URIs that are not resolved. Are you sure that \
                        you resolved all uris? This is expected when conducting a toy-run \
                        but should not happen elsewise.... continuing by ignoring missing uri \
                        : {}".format(uri))
                continue
            year = rd(int(gold_uri_loc_mapping[uri]["date"][0:4]))
            
            if macrotimes:
                if year in done \
                and done[year].get(dh.clean_loc_string(gold_uri_loc_mapping[uri]["given name"])) \
                and level == "macro":
                    continue

            elif any([dh.clean_loc_string(gold_uri_loc_mapping[uri]["given name"]) in done[k] for k in done]) \
            and level == "macro":
                continue
            
            # get gold
            yg = gold_uri_loc_mapping[uri]["lat-manual"]
            xg = gold_uri_loc_mapping[uri]["lng-manual"]

            if yg == "NA" or xg == "NA":
                continue
            yg = float(yg)
            xg = float(xg)
            if yg - xg < -5:
                #typo in the manual label
                continue
            gold.append((yg,xg))
            
            
            #get pred
            if level == "event":
                ythis = this_preds[uri]["prediction:"]["latitude"]
                xthis = this_preds[uri]["prediction:"]["longitude"]
            else:
                ythis = this_preds[uri]["prediction-center"]["latitude"]
                xthis = this_preds[uri]["prediction-center"]["longitude"]
             
            this.append([float(ythis),float(xthis)])

            if year not in done:
                done[year] = {}
            done[year][dh.clean_loc_string(gold_uri_loc_mapping[uri]["given name"])] = True
            idx_uri[idx] = uri
            idx+=1
            years.append(year)
        return this, gold, years
    else:
        idxx=0
        names_gold = {}
        for uri in gold_uri_loc_mapping:
            if uri not in this_preds:
                logging.warning("found URIs that are not resolved. Are you sure that \
                        you resolved all uris? This is expected when conducting a toy-run \
                        but should not happen elsewise.... continuing by ignoring missing uri \
                        : {}".format(uri))
                continue
            if macrotimes:
                if year in done and done[year].get(dh.clean_loc_string(gold_uri_loc_mapping[uri]["given name"])) \
                        and level == "macro":
                    continue
            elif any([dh.clean_loc_string(gold_uri_loc_mapping[uri]["given name"]) in done[k] for k in done]) \
                    and level == "macro":
                continue
            yg = gold_uri_loc_mapping[uri]["lat-manual"]
            xg = gold_uri_loc_mapping[uri]["lng-manual"]

            if yg == "NA" or xg == "NA":
                continue
            yg = float(yg)
            xg = float(xg)
            if yg - xg < -5:
                #typo in the manual label
                continue
            names_gold[dh.clean_loc_string(gold_uri_loc_mapping[uri]["given name"])] = (yg,xg)
                
        for uri in this_preds:
            year = rd(int(gold_uri_loc_mapping[uri]["date"][0:4]))
            for idx in this_preds[uri]["ents"]:
                
                if "prediction-center" not in this_preds[uri]["ents"][idx] \
                or "prediction" not in this_preds[uri]["ents"][idx]:
                    continue
                if level == "macro":
                    if this_preds[uri]["ents"][idx]["prediction-center"] == UNKNOWN:
                        continue
                    if "INTERPOLATION" in this_preds[uri]["ents"][idx]["prediction-center"]["asciiname"]:
                        continue
                else:
                    if this_preds[uri]["ents"][idx]["prediction"] == UNKNOWN:
                        continue
                    if "INTERPOLATION" in this_preds[uri]["ents"][idx]["prediction"]["asciiname"]:
                        continue
                
                text = dh.clean_loc_string(this_preds[uri]["ents"][idx]["used_name"])
                tup = names_gold.get(text)

                if not tup:
                    continue
                if macrotimes:
                    if year in done[year].get(text) \
                            and level == "macro":
                                continue
                elif any([text in done[k] for k in done]) \
                        and level == "macro":
                    continue
                yg = tup[0]
                xg = tup[1]
                
                if yg - xg < -5:
                    continue
                if level == "event":
                    yt = this_preds[uri]["ents"][idx]["prediction"]["latitude"]
                    xt = this_preds[uri]["ents"][idx]["prediction"]["longitude"]
                else:
                    yt =  this_preds[uri]["ents"][idx]["prediction-center"]["latitude"]
                    xt =  this_preds[uri]["ents"][idx]["prediction-center"]["longitude"]
                                
                this.append([float(yt),float(xt)])
                gold.append([yg,xg])
                
                if year not in done:
                    done[year] = {}
                done[year][text] = True

                idx_uri[idx] = uri
                idxx+=1
                years.append(year)
        return this, gold, years


def evaluate(pred_uri_loc_mapping, gold_uri_loc_mapping, level = "event"):
    this, gold, years = get_data(pred_uri_loc_mapping
            , gold_uri_loc_mapping
            , level=level
            , text_places=False)    
    km_deltas_this = [vincenty(this[i],gold[i]).km for i in range(len(gold))]
    dates = [i for i in range(len(years)) if years[i]  > 700 and years[i] < 1525]
    print(list(sorted(list(set(years)))))
    if not level == "macro":
        if args.times:
            datedict = {"century": [years[i] for i in dates]
                    , "km delta": [km_deltas_this[i] for i in dates]}
            
            s=0
            
            string = "{} & {} & {} ".format("decade"
                    ,"median km delta this"
                    ,"cumulative median km delta this")
            outd = {"time": [],"delta": [], "delta-cumulative":[]} 
            for y in sorted(list(set(datedict["century"]))):
                dt = [datedict["km delta"][i] for i in range(len(datedict["km delta"])) 
                        if datedict["century"][i] == y]
                
                delta= np.median(dt)
                s+=delta
                #print(s,s2)
                string+=" \\\\\n{} & {} & {} ".format(y
                        ,delta
                        ,s)
                outd["time"].append(y)
                outd["delta"].append(delta)
                outd["delta-cumulative"].append(s)
            print(outd)
            print(string)
    else:
        thist, goldt, yearst = get_data(pred_uri_loc_mapping
                , gold_uri_loc_mapping
                , level=level
                , text_places=False
                , macrotimes = True)    
        km_deltas_thist = [vincenty(thist[i],goldt[i]).km for i in range(len(goldt))]
        datest = [i for i in range(len(yearst)) if yearst[i]  > 700 and yearst[i] < 1525]
        if args.times:
            datedict = {"century": [yearst[i] for i in datest]
                    , "km delta": [km_deltas_thist[i] for i in datest]}
            
            s=0
            string = "{} & {} & {} ".format("decade"
                    ,"median km delta"
                    ,"median km delta this")
            #outd = {"time":[],"delta":[], "delta-cumulative":[]} 
            outd = {"time": [], "delta":[], "delta-cumulative": []} 
            for y in sorted(list(set(datedict["century"]))):
                dt = [datedict["km delta"][i] for i in range(len(datedict["km delta"])) 
                        if datedict["century"][i] == y]
                delta = np.median(dt)
                s+=delta
                #print(s,s2)
                string+=" \\\\\n{} & {} & {} ".format(y
                        ,delta
                        ,s)
                outd["time"].append(y)
                outd["delta"].append(delta)
                outd["delta-cumulative"].append(s)
            print(outd)
            print(string)

    mean_delta_this = np.mean(km_deltas_this)
    
    def p(num,x):
        return round(num*100, 1)
    
    print(len(this),len(gold)) 
    print("latitude pearsor", pearsonr([x[0] for x in this],[x[0] for x in gold]))    
    print("longitude pearsor", pearsonr([x[1] for x in this],[x[1] for x in gold]))
    print("latitude rmse", np.sqrt(mean_squared_error([x[0] for x in this],[x[0] for x in gold])))
    print("longitude rmse", np.sqrt(mean_squared_error([x[1] for x in this],[x[1] for x in gold])))
    print("mean delta km",mean_delta_this)

    print("percentile deviations:")
    for k in range(50,100,5):
        print("\t{}\t{}".format(k,np.percentile(km_deltas_this,k)))
    
    print("higher better","max:",len([x for x in km_deltas_this]))
    print("# < 5km",len([x for x in km_deltas_this if x < 5])
            ,len([x for x in km_deltas_this if x < 5])/len([x for x in km_deltas_this]))
                
    print("# < 15km",len([x for x in km_deltas_this if x < 15])
            ,len([x for x in km_deltas_this if x < 15])/len([x for x in km_deltas_this]))
    
    print("# < 25km",len([x for x in km_deltas_this if x < 25])
            ,len([x for x in km_deltas_this if x < 25])/len([x for x in km_deltas_this]))
    
    print("# < 50km",len([x for x in km_deltas_this if x < 50])
            ,len([x for x in km_deltas_this if x < 50])/len([x for x in km_deltas_this]))
    
    print("# < 100km",len([x for x in km_deltas_this if x < 100])
            ,len([x for x in km_deltas_this if x < 100])/len([x for x in km_deltas_this]))

    print("lower better")
    print("# > 250km",len([x for x in km_deltas_this if x > 250])
            ,len([x for x in km_deltas_this if x > 250])/len([x for x in km_deltas_this]))
    
    print("# > 750km",len([x for x in km_deltas_this if x > 750])
            ,len([x for x in km_deltas_this if x > 750])/len([x for x in km_deltas_this]))
    
    
    print("# > 1000km",len([x for x in km_deltas_this if x > 1000])
            ,len([x for x in km_deltas_this if x > 1000])/len([x for x in km_deltas_this]))
    
    print("# > 2500km",len([x for x in km_deltas_this if x > 2500])
            ,len([x for x in km_deltas_this if x > 2500])/len([x for x in km_deltas_this]))
    

def evaluate_text_places(pred_uri_loc_mapping, gold_uri_loc_mapping, level = "event"):

    this, gold, years = get_data(pred_uri_loc_mapping
            , gold_uri_loc_mapping
            , level=level
            , text_places=True)    
    km_deltas_this = [vincenty(this[i],gold[i]).km for i in range(len(gold))]
    dates = [i for i in range(len(years)) if years[i]  > 700 and years[i] < 1525]
    
    
    if args.times:
        datedict = {"century":[years[i] for i in dates]
                , "km delta":[km_deltas_this[i] for i in dates]}
        
        
        string = "{} & {} & {}".format("decade"
                ,"median km delta this"
                ,"cumulative km delta")
        s = 0 
        for y in sorted(list(set(datedict["century"]))):
            dt = [datedict["km delta"][i] for i in range(len(datedict["km delta"])) 
                    if datedict["century"][i] == y]
            delta = np.median(dt)
            s+=delta_delta
            #print(s,s2)
            string+=" \\\\\n{} & {} & {} ".format(y
                    ,delta
                    ,s)
        print(outd)
        print(string)
    
    mean_delta_this = np.mean(km_deltas_this)
    
    def p(num,x):
        return round(num*100, 1)
    
    print("latitude pearsor", pearsonr([x[0] for x in this],[x[0] for x in gold]))
    print("longitude pearsor", pearsonr([x[1] for x in this],[x[1] for x in gold]))
    print("latitude rmse", np.sqrt(mean_squared_error([x[0] for x in this],[x[0] for x in gold])))
    print("longitude rmse", np.sqrt(mean_squared_error([x[1] for x in this],[x[1] for x in gold])))
    
    print("mean deviation to gold in km",mean_delta_this)#, "vs", mean_delta_o19)

    print("percentile deviations:")
    for k in range(50,100,5):
        print("\t{}\t{}".format(k,np.percentile(km_deltas_this,k)))
            
            #,[np.percentile(km_deltas_this,k) for k in range(50,100,5)])
    
    
    print("higher better", "max:",len([x for x in km_deltas_this]))
    print("# < 5km",len([x for x in km_deltas_this if x < 5]))
    print("# < 15km-event",len([x for x in km_deltas_this if x < 15]))
    print("# < 25km-event",len([x for x in km_deltas_this if x < 25]))
    print("# < 50km-event",len([x for x in km_deltas_this if x < 50]))
    print("# < 100km-event",len([x for x in km_deltas_this if x < 100]))
    print("lower better")
    print("# > 250km",len([x for x in km_deltas_this if x > 250]))
    print("# > 750km",len([x for x in km_deltas_this if x > 750]))
    print("# > 1000km",len([x for x in km_deltas_this if x > 1000]))
    print("# > 2500km",len([x for x in km_deltas_this if x > 2500]))
    
    
if __name__ == "__main__":
    args = get_args()
    with open(args.RI_as_json_path) as f:
        RI = {dat["uri"]:dat for dat in json.load(f)}
    with open(args.itinerary_file) as f:
        pred_uri_loc_mapping = json.load(f)
    #man = load_manual(args.gold_csv_path)
    gold_uri_loc_mapping = create_gold_uri_loc_mapping(RI, args.gold_csv_path, args.human_anno_type)
    with open(args.itinerary_file) as f:
        pred_uri_loc_papping = json.load(f) 
    if "charter_locations" in args.itinerary_file:
        evaluate(pred_uri_loc_mapping, gold_uri_loc_mapping, args.level)
    elif "NE_locations" in args.itinerary_file:
        evaluate_text_places(pred_uri_loc_mapping, gold_uri_loc_mapping, args.level)

