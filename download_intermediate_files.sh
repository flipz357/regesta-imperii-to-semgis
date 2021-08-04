#!/usr/bin/env bash

wget -O ri-data/RI.json https://www.cl.uni-heidelberg.de/~opitz/data/rigeo/RI.json
wget -O src/resources/ENTITIES_1.json https://www.cl.uni-heidelberg.de/~opitz/data/rigeo/ENTITIES_1.json
wget -O src/resources/CANDIDATES_1.json https://www.cl.uni-heidelberg.de/~opitz/data/rigeo/CANDIDATES_1.json
echo "Finished download"
