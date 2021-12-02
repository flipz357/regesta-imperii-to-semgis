#!/usr/bin/env bash

cd src

runid=999999

echo "starting pipeline and generate files from scratch"
echo "cleaning up old filed"

# delete old files

rm predictions/charter_locations_$runid.json
rm predictions/NE_locations_$runid.json

echo "starting joint resolution"

python main.py \
    -runid $runid \
    -log_level 1 \
    -place_candidate_file_path resources/CANDIDATES_1.json \
    -entity_file_path resources/ENTITIES_1.json \
    -ner_method spacy \
    -text_place_solver hillclimber \
    --interpolate_missing_text_place_predictions \
    --simple_candidate_extension

python add_automatic_centers_to_predictions.py \
    -itinerary_file predictions/charter_locations_$runid.json \
    -ner_place_file predictions/NE_locations_$runid.json \
    --solve_jointly

# evaluate: set -level macro for unique place names and -level micro for all occuring place names

echo "evaluate itinerary error"

python evaluate_with_gold_csv.py \
    -input_file predictions/charter_locations_$runid-_centers_added.json \
    -level macro

echo "evaluate text place error"

python evaluate_with_gold_csv.py \
    -input_file predictions/NE_locations_$runid-_centers_added.json \
    -level macro

cd ..
