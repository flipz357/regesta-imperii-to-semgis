from collections import Counter,defaultdict
from geopy.distance import vincenty
import numpy as np
from scipy.spatial.distance import cosine
from constants import UNKNOWN, UNKNOWN_ID


def use_id_voter_simple_on_list(predicted_ids, used_names):
    """ chose most frequent id for each name.

    E.g. ids = [x,y,z,y] names = [a,a, b,a] ---> [y,y,z,y]

    Args:
        predicted_ids (list): list with ids
        used_names (list): list with names
    Return:
        list with ids
    """
    for i,elm in enumerate(used_names):
        if elm == UNKNOWN:
            predicted_ids[i] = UNKNOWN_ID
    clf = Voter(method="idvoter")
    predicted_ids = clf.transform(predicted_ids,used_names)
    for i in range(len(predicted_ids)):
        if predicted_ids[i] == UNKNOWN_ID:
            predicted_ids[i] = predicted_ids[i-1]
    return predicted_ids

def use_dist_voter_simple_on_list(predicted_ids, used_names, geodat):
    """ chose most centered id for each name.

    E.g. ids = [x,y,z,y] names = [a,a, b,a] ---> [y,y,z,y]

    Args:
        predicted_ids (list): list with ids
        used_names (list): list with names
        geodat (dict): our geo data with coordinates that we need to determine
            the most centered point
    Return:
        list with ids
    """
    for i,elm in enumerate(used_names):
        if elm == UNKNOWN:
            predicted_ids[i] = UNKNOWN_ID
    clf = Voter(method="center",geodat=geodat)
    predicted_ids = clf.transform(predicted_ids,used_names)
    for i in range(len(predicted_ids)):
        if predicted_ids[i] == UNKNOWN_ID:
            predicted_ids[i] = predicted_ids[i-1]
    return predicted_ids

class Voter:

    def __init__(self,method="idvoter",geodat=None):
        self.method = method
        self.geodat = geodat

    def transform(self,Xids,Xnames):
        return self._transform_xs(Xids,Xnames)
    
    def _transform_xs(self,Xids,Xnames):
        if self.method == "idvoter":
            cd =self.gen_mfs_from_xs(Xids,Xnames)

        elif self.method == "center":
            cd =self.gen_centered_from_xs(Xids,Xnames)
        out = []
        for i,name in enumerate(Xnames):
            out.append(cd[name])
        return out
    
    def gen_mfs_from_xs(self,Xids,Xnames):
        cd = defaultdict(list)
        for i,name in enumerate(Xnames):
            cd[name].append(Xids[i])
        cd = {name:Counter(xs).most_common(1)[0][0] for name,xs in cd.items()}
        return cd
    
    def gen_centered_from_xs(self,Xids,Xnames):
        cd = defaultdict(list)
        for i,name in enumerate(Xnames):
            cd[name].append(Xids[i])
        centers = {}
        for name in cd:
            latx=[]
            lngx=[]
            for idx in cd[name]:
                data  =self.geodat.get(idx)
                if data:
                    latx.append(float(data[0]))
                    lngx.append(float(data[1]))

        for i,name in enumerate(cd):
            tmpd = 10000000.00
            tmp = None
            if name == UNKNOWN:
                continue
            for j,idx in enumerate(cd[name]):
                data = self.geodat.get(idx)
                s = 0.0
                for k, idx2 in enumerate(cd[name]):
                    data2 = self.geodat.get(idx2)
                    if j <= k:
                        continue
                    if not data or not data2:
                        continue
                    d=cosine([float(x) for x in list(data)],[float(x) for x in list(data2)])
                    s+=d
                if s < tmpd:
                    tmpd = s
                    tmp = idx
            if tmp:
                cd[name] = tmp
            else:
                cd[name] = UNKNOWN_ID
        return cd
    




