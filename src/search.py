import numpy as np
import networkx as nx
from networkx.algorithms.approximation import steinertree
import logging
from random import shuffle, choice
from collections import Counter


def safe_get(i, ls):
    if len(ls) > i:
        return ls[i]
    if not ls:
        return []
    else:
        return ls[0]


def search(stations
        , C
        , queryobject
        , init_station="-1"
        , init_memory=([0.0], [["99999999"]], ["99999999"])
        , places_in_regests = [[]]):
    """Search shortest route
    
    Given a list of place names travel stations and a Candidate data base 
    name ---> goeids, find the geoid sequence which minimzes cost, e.g.,
    l=[Rome,Pisa,Rome]; C={Rome:[0,1,2], Pisa:[5,19,25,13]} ----> [1,25,1]

    Args:
        stations (list): list with place names, e.g. [Rome,Pisa,Rome]
        C (dict): mapping that maps from a place name to a list with 
            geonameid candidates,e.g. C={Rome:[0,1,2], Pisa:[5,19,25,13]}
        queryobject (QueryObject): an object that computes distances 
            between geoname ids
        init_station (string): dummy index, start node,default="-1"
        init_memory (tuple): dummy start memory,
            default=see above
        places_in_regests (list): list of lists with geonameids occuring in 
        charter text that allow us to debugrm the location of charter creation,
            e.g. [ [12,34,2],[0],[1,23,421,12] ]

    Returns:
        list: list with strings, the predictid geoname ids for the input
        float: cumulative distance for the path

    """

    out = []
    memory={}
    memory[-1] = init_memory
    last_station = init_station
    
    #we iterate over the stations
    for i,station in enumerate(stations):
        logging.debug("resolving: {}".format(station))
        
        #we get the candidates for this station
        geo_ids = C[station]
        
        logging.debug("candidates found: {}".format(len(geo_ids)))

        #we get the cum cost, the possible pathes and the last geoids for 
        #every candidate from t-1
        cum_dist, pathes, geo_ids_last = memory[i-1]
        
        #we init a matrix to store costs from every candidate at t to 
        #every candidate from the last step t-1 (plus the cumulative cost
        #for traveling to t-1) 
        cdists = np.zeros( (len(geo_ids), len(geo_ids_last)))
        
        logging.debug("computing dist mat of shape {}...".format(cdists.shape))
        # we iterate over candidates of t
        for j, idx in enumerate(geo_ids):
            #and we iterate over candidates from t-1
            for k,idx_last in enumerate(geo_ids_last):
                #we calculate the cost from a candidate at t to a candidate at t-1
                if i > 0:
                    dist = queryobject.cost(stations[i-1], idx_last,station,idx,
                            helper_places=safe_get(i, places_in_regests) )
                else:
                    dist = queryobject._maybe_inform_with_helper_places(idx
                            , queryobject._compute_feavec(station, idx)
                            , helper_places=safe_get(i, places_in_regests)
                            )
                #and store the cost in the matrix added to the cost that we paid
                #to traveling to the candidate from the last step
                cdists[j][k] =cum_dist[k]+ dist 
        logging.debug("finshed. min cumulative dist {}, max cumulative dist\
                {}".format(cdists.min(), cdists.max()))
        
        #for every candidate at t we get the candidate at t-1 with min cost 
        #for traveling to t via  t-1
        argmins = cdists.argmin(1)
        
        
        tmpcumdists = []
        tmppathes = []
        tmpcoordinates_last = []
        
        logging.debug("updating memory t-1 = t")
        
        #we update now the memory
        #we iterate over the candidates at t
        for j in range(cdists.shape[0]):
            #get the best last candidate at t-1
            argmin = argmins[j]
            #update the pathes and cumulative costs
            tmppathes.append(pathes[argmin]+[j])
            tmpcumdists.append(cdists[j][argmin])
            tmpcoordinates_last.append(geo_ids[j])
        
        memory[i] = (tmpcumdists, tmppathes, tmpcoordinates_last)
        memory.pop(i-1)
        logging.debug("memory updated")
        last_station = station
        if i % 10 == 0:
            logging.debug("placenames resolved: {}/{}".format(i, len(stations)))
        if (i + 1) % 100 == 0:
            logging.info("placenames resolved: {}/{}".format(i+1, len(stations)))

    logging.debug("finished... returning shortest path")
    cum_dist, pathes, coordinates_last = memory[len(stations)-1]
    amin = np.argmin(cum_dist)
    return pathes[amin], cum_dist[amin]


def _retrieve(name, G):
    x = ""
    triples = [a for a in G.edges(data=True)]
    ls = []
    for t in triples:
        if name in t[0]:
            x = t[1]
        elif name in t[1]:
            x = t[0]
        else:
            continue
        ls.append( (_graph_weight_delta(G,name), x) )
    ls = sorted(ls,key=lambda x:x[0])
    return ls[0][1]


def maybe_only_one(queryobject, names, idx_charter_location, V):
    if len(names) > 1:
        return  [],0.0
    if len(names) == 1:
        if idx_charter_location:

            result = [queryobject._vd_by_idx(idx, idx_charter_location[0]) 
                    for idx in V[0]]

            amin = np.argmin(result)
            return [V[0][amin]], result[amin]
        else:
            return [V[0][0]], 0.0


def gen_partitions(index, n=5): 
    index = index
    shuffle(index)
    chunks = [index[i:i+n] for i in range(0, len(index), n)]
    if len(chunks[-1]) < n:
        chunks[-2] = chunks[-2] + chunks[-1]
        chunks = chunks[:-1]
    return chunks


def topksteiner(names
        ,C
        ,queryobject
        ,idx_charter_location
        ,k=2
        ,random_starts=5
        ,n=5):

    score_dict = {names[i]:[] for i in range(len(names))}
    for i in range(random_starts):
        logging.debug("{}/{} random iteration".format(i, random_starts))
        partitions = gen_partitions(names, n)
        for partition in partitions:
            namesbar = partition
            
            out, _ = determine_with_steiner_tree(namesbar
                    , C
                    , queryobject
                    , idx_charter_location)

            for i,name in enumerate(namesbar):
                score_dict[name]+=[out[i]]
        logging.debug("finished iteration...collecting solutions".format(
            i, random_starts))
    score_dict = {k:Counter(v) for k, v in score_dict.items()}
    Vnew = []
    for name in names:
        top = [x for x,y in score_dict[name].most_common(k)[:k]]
        Vnew.append(top)
    return Vnew


def _pre_check_and_get_candidates(names, C, queryobject, idx_charter_location=[]):
    if not names:
        return [] , [], 0.0
    #names = list(set(names))
    logging.debug("names: {}".format(names))
    V = [list(set(C[name])) for name in names]
    logging.debug("current workload, \
            placenamecandidates={}".format([len(x) for x in V]))
    oo,c = maybe_only_one(queryobject,names,idx_charter_location,V)
    if oo:
        return [],oo,c
    else:
        return V, [],[]


def determine_with_steiner_tree(names
        , C
        , queryobject
        , idx_charter_location=[]
        , maxlen=5):
    
    maybeV, maybesolution, maybecost = _pre_check_and_get_candidates(names
            ,C
            ,queryobject
            ,idx_charter_location=idx_charter_location)
    if not maybeV:
        return maybesolution, maybecost
    else:
        V = maybeV
    logging.debug("instating candidate graph for {} names".format(len(names)))
    G = nx.Graph()
    if len(names) > maxlen*2 - 1:
        logging.debug("number of names ({}) exceeds set limit ({})... \
                partitioning the name set and solving individual parts \
                to reduce candidates".format(len(names),maxlen))
        logging.debug("heuristic starts...")
        
        V = topksteiner(names
                ,C
                ,queryobject
                ,idx_charter_location
                ,k=2
                ,random_starts=5
                ,n=maxlen)

        logging.debug("finished...current workload, \
                placenamecandidates={},".format([len(x) for x in V]))
    for i,idxset in enumerate(V):
        for j,idxset_other in enumerate(V):
            if i >= j:
                continue

            for k,idx in enumerate(idxset):
                for m,idx_other in enumerate(idxset_other):
                    if not G.has_edge(idx, idx_other):
                        
                        G.add_edge(idx,idx_other,weight=queryobject.cost(
                            names[i]
                            , idx
                            , names[j]
                            , idx_other
                            , idx_charter_location)
                            )
                    #G.add_edge(idx,names[i],weight=0.0)
    
    
    logging.debug("instated graph, graph debug: {}".format(nx.debug(G))) 
    logging.debug("current workload, placenamecandidates={},".format(
        [len(x) for x in V]))
    
    very_large_number = 10000.00
    for i,name in enumerate(names):
        for j,idx in enumerate(V[i]):
            G.add_edge("name:"+name,idx, weight=very_large_number)

    logging.debug("approximating Steiner tree".format(nx.debug(G))) 
    res = steinertree.steiner_tree(G,["name:" + n for i, n in enumerate(names)])
    #res = steinertree.steiner_tree(res,["name:"+n for n in names])

    res = nx.Graph(res)
    logging.debug("Steiner tree approximate, graph debug: {}".format(
        nx.debug(res)))
    
    triples = [a for a in res.edges(data=True)]
    logging.debug("Steiner graph triples: {}".format(triples))
    
    #gather solutions
    sols = []
    for i,n in enumerate(names):
        sols.append(_retrieve("name:"+n, res))
        res.remove_node("name:" + n)
    
    cum_weight = _get_cum_weight(sols
            , graph=None
            , query_object=queryobject
            , names=names
            , idx_charter_location=idx_charter_location)

    logging.debug("minimum cost: {}, result of hillclimbing: {}".format(
        cum_weight, sols))
    return sols, cum_weight


def _get_cum_weight(idxs
        , graph=None
        , query_object=None
        , names=[]
        , idx_charter_location=[]):
    
    s=0.0
    if not query_object:
        for i, idx in enumerate(idxs):
            for j, idx2 in enumerate(idxs):
                if idx == idx2:
                    continue
                s += graph[idx][idx2]["weight"]
    else:
        for i, idx in enumerate(idxs):
            for j, idx2 in enumerate(idxs):
                if idx == idx2:
                    continue
                s += query_object.cost(names[i]
                        , idx
                        , names[j]
                        , idx2
                        , idx_charter_location)

    return s/(len(idxs)**2)


def _graph_weight_delta(G, node):
    return G.degree(node, weight="weight")


def determine_with_stochastic_arrangement(names
        , C
        , queryobject
        , idx_charter_location=[]
        , iters=10):
    
    maybeV, maybesolution, maybecost = _pre_check_and_get_candidates(names
            ,C
            ,queryobject
            ,idx_charter_location=idx_charter_location
            )

    if not maybeV:
        return maybesolution, maybecost
    else:
        V = maybeV
    
    logging.debug("instating candidate graph for {} names".format(len(names)))
    

    minw = 10000000
    sp = []
    idxs = list(range(len(names)))

    # we select random sortings of the names and solve them with search
    for i in range(iters):
        idxsbar = list(range(len(names)))
        if i != 0:
            shuffle(idxsbar)
        namesbar = [names[i] for i in idxsbar]
        path,weight = search(namesbar
                , C
                , queryobject
                ,init_station="-1"
                ,init_memory=([0.0], [["99999999"]], ["99999999"])
                ,places_in_regests = [idx_charter_location])
        if weight < minw:
            minw = weight
            sp = path
            idxs = list(idxsbar)

    #we gather and return the solutions
    sols = [C[names[i]][sp[1:][idxs.index(i)]] for i in range(len(names))]
    
    cum_weight = _get_cum_weight(sols
            , graph=None
            , query_object=queryobject
            , names=names
            , idx_charter_location=idx_charter_location
            )

    logging.debug("minimum cost: {}, result of hillclimbing: {}".format(
        cum_weight, sols))
    return sols, cum_weight

def highest_pop_count(queryobject, names, C):
    hc = 0
    nameidx = 0
    placeidx = 0
    for i, name in enumerate(names):
        for j,idx in enumerate(C[name]):
            pop = queryobject._maybe_population(idx)
            if pop > hc:
                hc = pop
                nameidx = i
                placeidx = j
    return nameidx, placeidx, hc



def determine_with_hill_climber(names
        , C
        , queryobject
        , idx_charter_location=[]
        , iters=10
        , post_process_with_search=True
        , compute_cumulative_weight=False):
    
    maybeV, maybesolution, maybecost = _pre_check_and_get_candidates(names
            ,C
            ,queryobject
            ,idx_charter_location=idx_charter_location)

    if not maybeV:
        return maybesolution, maybecost
    else:
        V = maybeV
    logging.debug("instating candidate graph for {} names".format(len(names)))
    logging.debug("name stats: {}, {}".format(names, [len(C[name]) for name in names]))
     
    tmpnames = [names[0]]
    tmpidx = [C[names[0]][0]]
    tmpis = [0]
    cw = 0
    while len(tmpnames) < len(names):
        tmpw = 10000000
        tmpi=-1
        tmpc =None
        for i in range(len(names)):
            if i in tmpis:
                continue
            else:
                for c in C[names[i]]:
                    
                    d=queryobject.cost(tmpnames[-1]
                            ,tmpidx[-1]
                            ,names[i]
                            ,c
                            ,idx_charter_location)

                    if d < tmpw:
                        tmpw = d
                        tmpi = i
                        tmpc = c
        tmpidx.append(tmpc)
        tmpis.append(tmpi)
        tmpnames.append(names[tmpi])
        cw += tmpw
    
    #a little post processing with seach
    if post_process_with_search:
        path, weight = search(tmpnames, C, queryobject
                , init_station="-1",init_memory=([0.0], [["99999999"]], ["99999999"])
                , places_in_regests = [idx_charter_location])
        sols = [C[names[i]][path[1:][tmpis.index(i)]] for i in range(len(names))]
    else:
        sols = tmpidx
    
    if compute_cumulative_weight:
        cum_weight = _get_cum_weight(sols
                , graph=None
                , query_object=queryobject
                , names=names
                , idx_charter_location=idx_charter_location
                )
    else:
        cum_weight = cw
    logging.debug("minimum cost: {}, result of hillclimbing: {}".format(
        cum_weight, sols))
    
    return sols,cum_weight


def determine_with_random(names
        , C
        , queryobject
        , idx_charter_location=[]
        , iters=10):
    
    if not names:
        return [],0.0
    
    logging.debug("names: {}".format(names))
    V = [list(set(C[name])) for name in names]
    logging.debug("current workload, placenamecandidates={},".format(
        [len(x) for x in V]))
    sols = [choice(C[name]) for name in names]
    cum_weight = _get_cum_weight(sols
            , graph=None
            , query_object=queryobject
            , names=names
            , idx_charter_location=idx_charter_location)
    logging.debug("minimum cost: {}, result of hillclimbing: {}".format(
        cum_weight, sols))
    
    return sols, cum_weight


def resolve_places_in_regests(namess
        , C
        , queryobject
        , charter_location_idxs=[]
        , method="hillclimber"):

    helper_placess = [[safe_get(i,charter_location_idxs)] for i in range(len(namess))]
    out=[]
    if method == "hillclimber":
        method = determine_with_hill_climber
    elif method == "steiner":
        method = determine_with_steiner_tree
    elif method == "stochastic":
        method = determine_with_stochastic_arrangement
    elif method == "random":
        method = determine_with_random
    cumcost = []
    for i, names in enumerate(namess): 
        res,cost = method(names
                , C
                , queryobject
                , idx_charter_location=helper_placess[i]
                )

        out.append(res)
        cumcost.append(cost)
        logging.debug("{} regests processed (all placenames \
                inside text resolved)".format(i))
        if i % 100 == 0:
            logging.info("{} regests processed (all placenames\
                    inside text resolved)".format(i))
        
    return out, np.mean(cumcost)

