import gc
import sys
import logging
import numpy as np
import multiprocess as mp
import functools
import time
import Levenshtein
from constants import UNKNOWN


def dummy_info_dict(y, x, interpolidxs=[""]):
    idxs = "_".join(list(sorted(interpolidxs)))
    colnames = ["geonameid"
            , "name"
            , "asciiname"
            , "latitude"
            , "longitude"
            , "population"]
    dic = {}
    dic["geonameid"] = "INTERPOLATION_"+idxs
    dic["name"] = "INTERPOLATION_NONAME"
    dic["asciiname"] = "INTERPOLATION_NONAME"
    dic["latitude"] = y
    dic["longitude"] = x
    dic["population"] = -1
    return dic


def read_geo_names(paths=["../geodata/allCountries.txt","../geodata/alternateNames.txt"], return_inverted_index=True, latlngminmax=[(31,58),(-9.5,38)]):
    
    """    
    The main 'geoname' table has the following fields :
    ---------------------------------------------------
    geonameid         : integer id of record in geonames database
    name              : name of geographical point (utf8) varchar(200)
    asciiname         : name of geographical point in plain ascii characters, varchar(200)
    alternatenames    : alternatenames, comma separated, ascii names automatically transliterated, convenience attribute from alternatename table, varchar(10000)
    latitude          : latitude in decimal degrees (wgs84)
    longitude         : longitude in decimal degrees (wgs84)
    feature class     : see http://www.geonames.org/export/codes.html, char(1)
    feature code      : see http://www.geonames.org/export/codes.html, varchar(10)
    country code      : ISO-3166 2-letter country code, 2 characters
    cc2               : alternate country codes, comma separated, ISO-3166 2-letter country code, 200 characters
    admin1 code       : fipscode (subject to change to iso code), see exceptions below, see file admin1Codes.txt for display names of this code; varchar(20)
    admin2 code       : code for the second administrative division, a county in the US, see file admin2Codes.txt; varchar(80) 
    admin3 code       : code for third level administrative division, varchar(20)
    admin4 code       : code for fourth level administrative division, varchar(20)
    population        : bigint (8 byte int) 
    elevation         : in meters, integer
    dem               : digital elevation model, srtm3 or gtopo30, average elevation of 3''x3'' (ca 90mx90m) or 30''x30'' (ca 900mx900m) area in meters, integer. srtm processed by cgiar/ciat.
    timezone          : the iana timezone id (see file timeZone.txt) varchar(40)
    modification date : date of last modification in yyyy-MM-dd format
    """ 
    colnames = [(0, "geonameid")
            ,(1, "name")
            ,(2, "asciiname")
            ,(3, "alternatenames")
            ,(4, "latitude")
            ,(5, "longitude")
            ,(14, "population")]
            
    
    out = {}
    kickedout=0
    with open(paths[0],"r") as f:
        counter = 0
        for line in f:
            spl = line.split("\t")
            
            if latlngminmax:
                if float(spl[4]) < latlngminmax[0][0] or float(spl[4]) > latlngminmax[0][1]:
                    kickedout+=1
                    continue
                if float(spl[5]) < latlngminmax[1][0] or float(spl[5]) > latlngminmax[1][1]:
                    kickedout+=1
                    continue
            
            idx = spl[0]
            out[idx] = {}
            for cn in colnames:
                if cn[1] == "alternatenames":
                    out[idx][cn[1]] = [string.strip() for string in spl[cn[0]].split(",")]
                else:
                    out[idx][cn[1]] = spl[cn[0]]
            #out[idx]["morealternatenames"] = []
            counter+=1
            if counter % 10000 == 0:
                logging.info("{} geonames names loaded".format(counter))
                logging.info("{} names kicked out due to exceeding lat lng minmax".format(kickedout))

    if not return_inverted_index:
        return out,None
    
    #build inv ind
    ii = {}
    logging.info("starting building inverted index...")
    for idx in out:
        names = [out[idx]["name"]]
        for n in out[idx]["alternatenames"]:
            names.append(n)
        
        for n in names:
            if n not in ii:
                ii[n] = [idx]
            else:
                ii[n].append(idx)
    logging.info("inverted index... finished; size: {}".format(len(ii)))
    return out,ii
        

def id_to_info_dict(idx, geodata):
    return {k:v for k,v in geodata[idx].items() if k != "alternatenames"}


def maybe_convert_dissimilar_placenames_to_unknown(names
        , C
        , geodata
        , lr=None
        , exceptionfun=lambda x,y:False):
    if not lr:
        return names
    other = []
    for i,n in enumerate(names):
        if n != UNKNOWN:
            candidate_idxs = C.get(n)
            if not candidate_idxs:
                logging.warning("missing in candidates, placename {}".format(n))
                names[i] = UNKNOWN+"({})".format(n)
                continue
            try:
                candidate_names = [geodata[idx]["name"] for idx in candidate_idxs] 
                altn = [geodata[idx]["alternatenames"] for idx in candidate_idxs]
            except KeyError:
                logging.warning("place uri {} not found in geodata base. \
                        Setting this place to UNKNOWN. The \
                        reason for this is probably that the geonames data\
                        base has been updated, i.e. a different version of\
                        geo data base isused.".format(candidate_idxs))
                names[i] = UNKNOWN+"({})".format(n)
                continue

            altnames = [j for i in altn for j in i]
            candidate_names+=altnames
            lrs = [Levenshtein.ratio(n,s) for s in candidate_names]
            
            maxlr = max(lrs)
            maxi = np.argmax(lrs)
            if maxlr < lr and not any([exceptionfun(n,s) for s in candidate_names]):
                logging.info("levenshtein ratio for {}:{}. Setting to unknown because < threshold {}".format(n, maxlr, lr))
                names[i] = UNKNOWN+"({})".format(candidate_names[maxi])
    return names
        

def create_sets(s):
    return [set(list(x)) for x in s.split()]


def _build(idxs):
    return idxs


def _build_candidates(name, ii=None, char_sets=None):    
    
    if name in ii:
        #if we know this name return its candidates
        a = time.time()
        x = _build(ii[name])
        b = time.time()
        return x
    else:
        #else look up similar names
        l=len(name)
        found = []
        a = time.time()
        b = time.time()
        a = time.time()
        othernames = [othername for othername in ii]
        dists = []
        md = 1000
        for othername in othernames:
            lendiff = abs(len(name) - len(othername))
            if lendiff > md:
                dists.append(1000)
            else:
                d=Levenshtein.distance(name, othername)
                dists.append(d)
                if d < md:
                    md = d
        for i,d in enumerate(dists):
            if d == md:
                found+=ii[othernames[i]]
        b = time.time()
        return _build(list(set(found)))

def build_candidates(uniq_locations, data=None, ii=None, multiprocessing=False):
    C = {}
    
    pool=None
    if multiprocessing:
        pccount = mp.cpu_count() // 1.2
        pccount = int(pccount)
        pool = mp.Pool(max(1,pccount))
        print(pccount)

    char_sets = {k:create_sets(k) for k in uniq_locations}
    if not pool:
        for i, name in enumerate(uniq_locations):
            logging.info("searching candidates for {}...".format(name))
            candidates = _build_candidates(name, ii=ii, char_sets=char_sets)
            logging.info("candidates found: {}".format(candidates))
            C[name] = candidates
            if i % 10 == 0:
                logging.info("{}/{} regest names processed, candidates created".format(i, len(uniq_locations)))
            if i % 1000 == 0:
                logging.critical("{}/{} regest names processed, candidates created".format(i, len(uniq_locations)))
    else:
        #DO not use crashes memory at the moment
        candidatess=pool.map(lambda name: _build_candidates(name, ii=ii, char_sets=char_sets), uniq_locations)
    return C


def maybe_extend_candidates(C, ii, strategy=None, entity_types={}):
    if not strategy:
        return None
    for name in C:
        if name in ii:
            continue
        if " " in name:
            spl = name.split()
            for tok in spl:
                if name in entity_types:
                    #prevent collecting for only "Burg", "Kloster", etc
                    continue
                if tok in ii:
                    for cand in ii[tok]:
                        if cand not in C[name]:
                            C[name].append(cand)
    return None
