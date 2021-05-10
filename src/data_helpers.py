import json
import pickle
from collections import Counter,defaultdict
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
import itertools
import numpy as np
import os
import _pickle
import io
import spacy
import logging
from constants import UNKNOWN, NOLOC, RI_RAW_PATH, RI_RAW_NAMESPACE



def clean_loc_string(loc, remove_lower=True):
    """Rudimentary cleaning of a place name

    Args:
        loc (str): place-name
        remove_lower (bool): e.g. in Rome ----> Rome
    Returns:
        string: the cleaned place name

    """
    loc = loc.strip()
    if loc in NOLOC:
        return UNKNOWN
    if loc.endswith("?"):
        loc = loc.replace("?", "")
    if loc.startswith("["):
        loc = loc.replace("[", "")
        loc = loc.replace("]", "")
    elif loc.startswith("(") and loc.endswith(")"):
        loc = loc.replace("(", "")
        loc = loc.replace(")", "")
    elif loc.endswith("("):
        loc = loc.replace("(", "")
    if loc.endswith("(!)"):
        loc = loc.replace("(!)", "")
    if loc.startswith("bei "):
        loc = loc.replace("bei ", "")
    if loc.endswith("?"):
        loc = loc.replace("?", "")
    if loc.endswith("."):
        loc = loc.replace(".", "")
    if loc.startswith("vor "):
        loc = loc.replace("vor ", "")
    if loc.startswith("apud"):
        loc = loc.replace("apud ", "")
    if loc.startswith("aput"):
        loc = loc.replace("aput ", "")
    if loc.startswith("ad "):
        loc = loc.replace("ad ", "")
    if loc.startswith("ap. "):
        loc = loc.replace("ap. ", "")
    if loc.startswith("in "):
        loc = loc.replace("in ", "")
    if loc.startswith("civ "):
        loc = loc.replace("civ ", "")
    if loc.endswith(" civ"):
        loc = loc.replace(" civ", "")
    loc = loc.strip()
    if remove_lower:
        string=loc.split()
        upperonly = " ".join([s for s in string if s[0].isupper()])
        if upperonly:
            loc = upperonly
        else:
            loc = UNKNOWN
    if loc in NOLOC:
        loc = UNKNOWN
    if len(loc) < 3:
        loc = UNKNOWN
    return loc


def save_obj(obj,path):
    _pickle.dump(obj,open(path,"wb"))

def load_obj(path):
    return _pickle.load(open(path,"rb"))


def regest_iter(path=RI_RAW_PATH):
    for coll in os.listdir(path):
        for key in os.listdir(path+"/"+coll):
            xmlfile = path+"/"+coll+"/"+key
            yield (coll,key,xmlfile)

def regests_to_ls(path=RI_RAW_PATH
        , persname=None
        , locname=None
        , maxamount=-1
        , ids=[]
        , specifickey=None
        , specificword=None):
    
    """ Iterate over the structured RI xml data base 
    and convert it into a dictionary.

    Works without any specified arguments when RI_RAW_PATH is correctly set.
    
    Args: 
        path: path to root dir of RI data
        persname: specifiy an issuer name to only retrieve regests 
            of charters issued of him
        locname: specify location name to only retrieve regests of charters 
            issued in that location 
        maxamount: only return maxamount regest (default: -1=all)
        ids: only return regests with certain uris (default return all)
        specifickey: print the path of a regest of specific uri
        specificword: print the regest info if the text contains a specific word
    
    Returns:
        regests converted to better processable python/json dict
    
    """
    
    c=0
    regests = []
    for coll,key,regpath in regest_iter():
        if maxamount != -1 and len(regests) == maxamount:
            return regests
        if ids and not c in ids:
            c+=1
            continue
        if specifickey and specifickey not in regpath:
            c+=1
            continue
        elif specifickey and specifickey in regpath:
            print(regpath,specifickey,"found")
        try:
            dic = {}
            et = ET.parse(regpath)
            reg_komm = extract_divtexts(et,["regestentext","kommentar","incipit"])
            zeugen = extract_otherpersons(et,string="zeugen")
            unterschr = extract_otherpersons(et,string="unterschriften")
            loc = extract_text(et,"origPlace")
            iss = extract_text(et,"persName", "role","issuer")
            if persname and persname != iss:
                continue
            if locname and locname != loc:
                continue
            date = extract_date(et)
            dic["regestentext_raw"] = reg_komm[0]
            dic["regestentext_clean"] = reg_komm[1]
            if specificword:
                if specificword not in dic["regestentext_clean"].lower():
                    c+=1
                    continue    
                else:
                    c+=1
                    print(key+"\t"+iss+"\t"+loc+"\t"+date[0]+"\t"+dic["regestentext_clean"])
                    print(c)
                    continue
            dic["kommentar_raw"] = reg_komm[2]
            dic["kommentar_clean"] = reg_komm[3]
            dic["incipit_raw"] = reg_komm[4]
            dic["incipit_clean"] = reg_komm[5]
            dic["zeugen"] = zeugen
            dic["unterschriften"] = unterschr
            dic["location"] = loc
            dic["issuer"] = iss
            dic["date"] = date
            dic["uri"] = key
            dic["collection"] = coll
            regests.append(dic)
        except ET.ParseError:
            continue
        c+=1
        if c% 1000 == 0:
            print(c," done",len(regests))
    return regests

def extract_date(et):
    fromto= []
    for ch in et.iter(RI_RAW_NAMESPACE+"origDate"):
        fromto.append(ch.attrib["from"])
        fromto.append(ch.attrib["to"])
    return fromto

def extract_otherpersons(et, string="zeugen"):
    l=[]
    for ch in yield_divs(et):
        if string in ch.attrib:
            count = 0
            for name in ch.iter("persName"):
                l.append(name.text)    
                count+=1
            if count == 0 and ch.text != None:
                l = ch.split(";")        
    return l


def yield_divs(et):
    for div in et.iter(RI_RAW_NAMESPACE+"div"):
        yield div

def extract_text(et
        , name
        , attr=""
        , val=""):
    count = 0
    string=""
    for ch in et.iter(RI_RAW_NAMESPACE+name):
        if attr == "":
            count+=1
            if count != 1:
                raise ValueError("more than one")
            else:
                string = ch.text     
        else:
            if attr in ch.attrib and ch.attrib[attr] == val:
                string = ch.text
    if string is None:
        return "-"
    return string



def clean_notes(string):
    while "<ns0:note " in string:
        ss = string.split("<ns0:note ", 1)
        ss2 = string.split("</ns0:note>", 1)
        try:
            string=ss[0] + ss2[1]
        except IndexError:
            print("malformed xml?",string)
            return string
    return string

def extract_divtexts(et, attribs):
    ls = []
    for div in yield_divs(et):
        for a in attribs:
            if div.attrib["type"] == a:
                for text in div.iter(RI_RAW_NAMESPACE+"p"):
                    if not True:
                        ls.append("None")
                        ls.append("None")
                    else:
                        string = BeautifulSoup(clean_notes(ET.tostring(text).decode()))
                        ls.append(string.text)
                        ls.append(string.text.replace("\t", ""))
    return ls


    
def readf(p):
    with open(p,"r") as f:
        string = f.read()
        return string

   
def writef(string,p):
    with open(p,"w") as f:
        f.write(string)


def regests2json(n, save_path="../ri-data/RI.json"):
    regests = regests_to_ls(maxamount=n)
    with open(save_path,"w") as f:
        f.write(json.dumps(regests, indent=4, sort_keys=True))
    return None

def loadjson(p="resources/RI.json"):
    with open(p,"r") as f:
        return json.load(f)

def maybe_associated_with_loc(ent, nlp):
    tokens = [t for t in ent]
    last_token = nlp(tokens[-1].text).ents
    if last_token and last_token[0].label_ == "LOC" and len([t for t in ent]) > 1:
        return last_token[0].text
    else:
        for i, t in enumerate(tokens):
            if t.text in ["von", "zu", "de"] and i < len(tokens) - 1:
                return tokens[i+1].text
        return UNKNOWN

def _extract_heads_from_tree(doc, token):
    pathrels = []
    maxiter=1000
    i = 0
    while token.dep_ != "ROOT" and i < maxiter:
        rel = token.dep_
        token = token.head
        pathrels.append(rel +" --> "+token.text+" & ")
        i+=1
    return pathrels

def _serialize_doc(doc):
    """Serializes preprocessed document"""
    tok = ""
    lemma = ""
    pos = ""
    dep = ""
    charoff = ""
    head=""
    tag=""
    for i,token in enumerate(doc):
        tok += token.text.strip()+" "
        lemma += token.lemma_.strip()+" "
        pos += token.pos_.strip()+" "
        dep += token.dep_.strip()+" "
        head += str(token.head.i)+" "
        tag += token.tag_+" "
        charoff += str(token.idx)+" "
    tok = tok.strip()
    lemma = lemma.strip()
    pos = pos.strip()
    dep = dep.strip()
    head = head.strip()
    tag = tag.strip()
    charoff = charoff.strip()
    l = ["#tok:::"      +tok
            ,"#lemma:::"+lemma
            ,"#pos:::"  +pos
            ,"#dep:::"  +dep
            ,"#head:::" +head
            ,"#tag:::"   +tag
            ,"#charoffset:::"+charoff]
    l = "\n".join(l)
    return l


def _get_ent_dict(label
        , text
        , associated_with_loc
        , heads, chstart
        , chend
        , tokstart
        , tokend
        , entity_type):

    dic = {"label": label
            , "text": text
            , "associated_with_loc": associated_with_loc
            , "heads": heads
            , "chstart": chstart
            , "chend": chend
            , "tokstart": tokstart
            , "tokend": tokend
            , "predicted_entity_type": entity_type
            }
    return dic

def _maybe_get_ent_type(entity, doc, entity_types, last_entity_type):
    text = entity.text
    #predicted entity type
    pred_type = ""
    for e in entity_types:
        if e in text:
            pred_type = entity_types[e]
    if not pred_type:
        if entity.start > 0:
            tok_before = doc[entity.start - 1]
            for e in entity_types:
                if e in tok_before.text:
                    pred_type = entity_types[e]
            if tok_before.text in ["u.", "und"] and not pred_type:
                pred_type = last_entity_type
    return pred_type


def _extract_nes(regesttext, nlp, entity_types):  
    """preprocess and extracts named ents"""
    regesttext = regesttext.replace("v.", "von")
    for key in entity_types:
        if key.endswith("."):
            #it's an abbreviated type --> spell out
            regesttext = regesttext.replace(key, entity_types[key])
    doc = nlp(regesttext)
    dic = {"serialization of preprocessed doc": _serialize_doc(doc), "ents": {}}
    i=0
    last_entity_type = ""
    for ent in doc.ents:
        label = ent.label_
        pathrels = _extract_heads_from_tree(doc, ent.root)
        entity_type = _maybe_get_ent_type(ent, doc, entity_types, last_entity_type)
        last_entity_type = entity_type
        if label == "LOC":
            dic["ents"][i] = _get_ent_dict(label
                    , ent.text
                    , ent.text
                    , pathrels
                    , ent.start_char
                    , ent.end_char
                    , ent.start
                    , ent.end
                    , entity_type
                    )
            i+=1

        elif label == "PER":
            dic["ents"][i] = _get_ent_dict(label
                    , ent.text
                    , maybe_associated_with_loc(ent, nlp)
                    , pathrels
                    , ent.start_char
                    , ent.end_char
                    , ent.start
                    , ent.end
                    , entity_type)
            i+=1
    return dic

        
"""
def _maybe_convert_ent_dict_to_actual_format(dic):
    
    for key in dic:
        if "ents" in dic[key]:
            return None
        else:
            break
    for key in dic:
        dic[key]["serialization of preprocessed doc"] = "NA"
        dic[key]["ents"] = {}
        for j in range(10000):
            if j in dic[key]:
                elm = dic[key].pop(j)
                dic[key]["ents"][j] = elm
            elif str(j) in dic[key]:
                j=str(j)
                elm = dic[key].pop(j)
                dic[key]["ents"][j] = elm
            else:
                break
    return None
"""
def _clean_nes(jsondic, cf=lambda x:x):
    """Cleans named entities with cleaning function
    """
    for k in jsondic:
        for k2 in jsondic[k]["ents"]:
            if jsondic[k]["ents"][k2]["label"] == "PER":
                jsondic[k]["ents"][k2]["associated_with_loc"] = cf(jsondic[k]["ents"][k2]["associated_with_loc"])
            elif jsondic[k]["ents"][k2]["label"] == "LOC":
                jsondic[k]["ents"][k2]["text"] = cf(jsondic[k]["ents"][k2]["text"])
    return None

def load_entity_types(p):
    etype_dict = {} 
    if not p:
        return {}
    with open(p, "r") as f:
        for line in f.read().split("\n"):
            line = line.strip()
            e1 = ""
            e2 = ""
            if " " in line:
                e1 = line.split()[0]
                e2 = line.split()[1]
            else:
                e1 = line
                e2 = line
            etype_dict[e1] = e2
    etype_dict.pop("")
    return etype_dict

def extract_nes(jsonregests, check_if_saved=True, clean=lambda x:x
        , save_path="resources/ENTITIES.json", method="spacy", entity_types={}):
    """NLP processing for entity extraction
    
    1. Processes regest texts with spacy/stanza
    2. extracts named entities that are associated with places 
        (either places themselves or e.g, nobles X of Y, where Y is a place)
    3. writes the found entities to disk
    """
    if check_if_saved:
        if os.path.exists(save_path):
            with open(save_path,"r") as f:
                dat = json.load(f)
            #_maybe_convert_ent_dict_to_actual_format(dat)
            _clean_nes(dat,clean)
            return dat
    
    if method == "spacy":
        logging.info("loading spacy de_core_news_lg")
        nlp = spacy.load('de_core_news_lg')

        logging.info("spacy model loaded")
    elif method == "stanza":
        logging.info("loading stanza pipeline")
        import stanza
        from spacy_stanza import StanzaLanguage

        snlp = stanza.Pipeline(lang="de")
        nlp = StanzaLanguage(snlp)
        logging.info("stanza pipeline loaded")
    out = {}
    for i,jr in enumerate(jsonregests):
        key = jr["uri"]
        out[key] = _extract_nes(jr["regestentext_clean"], nlp, entity_types=entity_types) 
        #print(jr["regestentext_clean"])
        if i % 1000 == 0:
            logging.info("{}/{} regests spacy processed".format(i, len(jsonregests)))
    _clean_nes(out,clean)
    with open(save_path,"w") as f:
        f.write(json.dumps(out))
    return out

def get_locs_vocab(entitydict):
    v = defaultdict(int)
    for key in entitydict:
        ents = entitydict[key]
        for ent in ents.values():
            if ent["label"] == "LOC":
                v[ent["text"]]+=1
            elif ent["label"] == "PER":
                if ent["associated_with_loc"] != UNKNOWN:
                    v[ent["associated_with_loc"]]+=1
    return v

def unknown_handling(input_names, strat="last"):
    """Interpolates missing place names
    
    Args:
        input names: list with strings, some of them UNKNOWN
        strat: interpolation strategy, default=last not unknown
    Returns:
        list without UNKNOWN names
    """
    names_not_unknown = []
    if strat == "last":
        for i,n in enumerate(input_names):
            if UNKNOWN in n:
                names_not_unknown.append([n for n in input_names[:i] if UNKNOWN not in n][-1])
            else:
                names_not_unknown.append(n)
    elif strat == "remove":
        for i,n in enumerate(input_names):
            if UNKNOWN not in n:
                names_not_unknown.append(n)
    return names_not_unknown


def load_manual(p):
    """load manual csv file that contains mapping place names to coordinates

    Args:
        p (string): file path to csv
    Returns:
        dictionary that maps names to coordinates
    """
    with open(p) as f:
        lines = [x for x in f.read().split("\n") if x != ""][1:]
    dic={}
    not_loaded = 0
    for l in lines:
        elms=l.split("|")
        origname = elms[3]
        normalizedname=elms[5]
        try:
            lat=float(elms[7])
            lng=float(elms[6])
        except ValueError:
            #print(l,"could not convert to float")
            not_loaded+=1
            continue
        dic[origname] = (normalizedname,lat,lng,elms[14])
    print("could load",len(lines)-not_loaded
            , "from the", len(lines),"gold name-place resolutions")
    return dic

def load_manual_geonamesid(p):
    """load manual csv file that contains mapping place names to geonameids

    Args:
        p (string): file path to csv
    Returns:
        dictionary that maps names to coordinates
    """
    with open(p) as f:
        lines = [x for x in f.read().split("\n") if x != ""][1:]
    dic={}
    not_loaded = 0
    for l in lines:
        elms=l.split("|")
        origname = elms[3]
        normalizedname=elms[5]
        gid = elms[10].split("/")[-1].strip()
        if gid:
            dic[origname] = gid
        else: 
            not_loaded+=1
            continue
    print("could load",len(lines)-not_loaded
            , "from the", len(lines),"gold name-place resolutions")
    return dic
