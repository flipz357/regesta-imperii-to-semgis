#!/usr/bin/env bash

mkdir ri-data
wget --no-check-certificate --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies 'https://docs.google.com/uc?export=download&id=1Ag4L_1ZvO_couLOQrLdsx1R4xDeihjHe' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1Ag4L_1ZvO_couLOQrLdsx1R4xDeihjHe" -O ri-data/RI.json && rm -rf /tmp/cookies.txt
echo "Finished download"
