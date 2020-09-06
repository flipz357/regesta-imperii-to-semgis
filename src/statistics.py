import numpy as np

def candidate_stats(dic):
    o=[]
    for name in dic:
        o.append(len(dic[name]))
    nkeys = len(dic)
    med = np.median(o)
    mean = np.mean(o)
    perc = [np.percentile(o,i) for i in [50,75,90,95,99]]

    return [nkeys,med,mean,perc]


