#!/usr/bin/env bash

wget -O geodata/allCountries.zip https://download.geonames.org/export/dump/allCountries.zip 
echo "Finished download, unzipping..."
unzip geodata/allCountries.zip -d geodata/
echo "Finished"
