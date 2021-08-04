import json
from geopy.distance import vincenty
import Levenshtein
import geohelpers as gh
import math
import numpy as np

def cost0(x, y):
    """simplest cost fo traveling from p=x to p'=y

    Args:
        x (list): list representing p with [lat, lng, ...]
        y (list): list representing p' with [lat, lng, ...]
   
    Returns:
        float: vincenty distance       
        float: vincenty distance
    """
    di = vincenty(( x[0],x[1]),(y[0],y[1])).km#/div
    return di, di

def cost1(x, y, vd=None, coef = [None, None, 1, 1, 0.25]):
    """advanced cost to traveling from p=x to p'=y

    Args:
        x (list): list representing p with [lat, lng, ...]
        y (list): list representing p' with [lat
            , lng
            , LevR from name of p' found in data base to actual name of p'
            , population count
            , avg. distance to helper places of p']
        vd: in case we have vincenty distance pre computed
        coef (list): weights for y
    Returns:
        float: traveling cost
        float: vincenty distance
    """

    levr = y[2] 
    pop = y[3] 
    avg_helper_dist = y[4]
    
    levr_coef = coef[2] 
    pop_coef = coef[3] 
    avg_helper_dist_coef = coef[4]
    
    if not vd:
        vd = vincenty( (x[0], x[1]),(y[0], y[1]) ).km
    
    numer = vd + avg_helper_dist_coef * avg_helper_dist
    
    denom = 1 + levr_coef * levr 
    denom += pop_coef*math.log(pop, 1000)
    
    return numer/denom, vd

class QueryObject:

    def __init__(self,geodata, costfun=cost0
            ,save_feas=True, save_dists=False):
        """ Inits object for distance/cost queries

        Args:
            geodata (dict): a dictionary that maps geonames indices to
                dictionaries that allow us to grab "latitude" "longitude"
                and "polulation" count
            costfun (placefeatures x placefeatures -> cost): 
                a function that calculates the cost between two places. can also
                incorporate other features such as population count.
            save_feas (bool): use memory to store calcluated place features
            save_dist (bool): use memory to store cost calculations. 
                Not recommended atm, blows up memory.
            ii (dict)

        """
        self.geodata = geodata
        self._cost = costfun
        self.saver= {}
        self.save_feas = save_feas
        self.save_dists = save_dists


    def _vd(self, x, y):
        return cost0(x,y)[0]
    
    def _vd_by_idx(self,idx,idxother):
        if not idx or not idxother:
            return 0.0
        y,x = self.geodata[idx]["latitude"], self.geodata[idx]["longitude"]
        ybar,xbar = self.geodata[idxother]["latitude"] ,self.geodata[idxother]["longitude"]
        return cost0( [y,x], [ybar, xbar])[0]
    
    def _maybe_population(self, pid):
        """returns the population count for a place id"""

        pop = float(self.geodata[pid]["population"])

        if not pop:
            return 1
        else:
            return int(pop)

    def _compute_feavec(self, pn, pid):
        """ Maps a place name and a place name id onto a feature vector

        Args:
            pn (string): place name
            pid (string): place name id (geonamesid)
        Returns:
            a vector [y, x, maxlr, pop] that describes a place
        """
            
        #levenshtein distance
        names = self.geodata[pid]["alternatenames"] + [self.geodata[pid]["name"]]
        
        lrs = [ Levenshtein.ratio(pn, x) for x in names]

        maxlr = max(lrs)

        #actual geopoint
        y,x = self.geodata[pid]["latitude"], self.geodata[pid]["longitude"]
        
        #population
        pop = self._maybe_population(pid)
        
        feavec = [y, x, maxlr, pop]
        feavec = [float(x) for x in feavec]
        return feavec

    def _maybe_inform_with_helper_places(self, placeid, feavec, helper_places=[]):
        """given a place id and its feature vector, return 
        distance to helper places
        
        Args:
            placeid (string): place id geonames
            feavec (list): vector that represents the place... lat, lng, pop count...
            helper_places (list): list with geonames ids of possible places in vicinity
        Returns:
            A float that represents the average distance to helper places
        """

        if not helper_places:
            return 0.0
        y,x = feavec[0], feavec[1]
        avg_dist = []
        
        for hp in helper_places:
            combi_key = "#".join(list(sorted([placeid,hp])))
            if self.save_dists and combi_key in self.saver:
                vd = self.saver[combi_key]
            else:
                ybar,xbar = self.geodata[hp]["latitude"], self.geodata[hp]["longitude"]
                vd = self._vd( (y, x), (ybar, xbar) )
            avg_dist.append(vd)
        
        if sum(avg_dist+[0.0]) > 0.01:
            return np.mean(avg_dist)
        else:
            return 0.0

    def cost(self, placename1, placeid1, placename2, placeid2, helper_places=[]):
        """compute cost of traveling from a place to the other

        Args:
            placename1 (string): name of the first place
            placeid1 (string): geonames id of the first place
            placename2 (string): name of the 2nd place
            placeid2 (string): geonames id of the 2nd place
            helper_places (list): list with geonames ids 
                                  of possible places in vicinity of the next place
        Returns:
            traveling cost (float).
        """

        if not any([placename1, placeid1, placename2]):
            return self._maybe_inform_with_helper_places(placeid2, feavec2, helper_places)
                
        key1 = placename1+ placeid1
        key2 =  placename2 + placeid2
        combi_key = "#".join(list(sorted([placeid1,placeid2])))
        vd = None
        if self.save_dists and combi_key in self.saver:
            vd = self.saver[combi_key]
        
        
        if self.save_feas and key1 in self.saver:
            feavec1 = self.saver[key1]
        else:
            feavec1 = self._compute_feavec(placename1, placeid1)
            self.saver[key1] = feavec1

        if self.save_feas and key2 in self.saver:
            feavec2 = self.saver[key2]
        else:
            feavec2 = self._compute_feavec(placename2, placeid2)
            self.saver[key2] = feavec2
        
        mh1 = self._maybe_inform_with_helper_places(placeid1, feavec1, helper_places)
        mh2 = self._maybe_inform_with_helper_places(placeid2, feavec2, helper_places)
        
        feavec1bar = feavec1+[mh1]
        
        feavec2bar = feavec2+[mh2]
        c,vdis = self._cost(feavec1bar, feavec2bar, vd=vd)
        if not vd and self.save_dists:
            self.saver[combi_key] = vdis
        return c

def get_center(idxs, geodat):
    """Returns the center of several places (avg. of lat and lng)"""

    ys = []
    xs = []
    for idx in idxs:
        ys.append(float(geodat[idx]["latitude"]))
        xs.append(float(geodat[idx]["longitude"]))
    return np.mean(ys), np.mean(xs)


