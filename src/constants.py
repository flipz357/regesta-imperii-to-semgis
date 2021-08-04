#!/usr/bin/env python
# -*- coding: utf-8 -*-


RI_RAW_PATH =  "../ri-crawler/regests_raw"
RI_RAW_NAMESPACE= "{http://www.tei-c.org/ns/1.0}"

NOLOC=set(["Ort", "O", "O.]", "Ebf", "Mog", "Mon", "–", "-", "–]"
    , "", "o O", "oO", "-", "u o O", "und o O", "u oO", "und oO"
    , "ohne ort", "ohne Ort", "Sine loco", "sine loco"
    , "et sine loco", "Jaffé"])

NOLOC.update({"....","sine loco","unb","unbekannt","?"})

UNKNOWN="UNKNOWN"
UNKNOWN_ID = -999999

