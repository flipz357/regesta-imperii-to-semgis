# Example tools for statistical medieval analyses 

Based on the output files of this project.

## Example 1: create a spatially grounded medieval KG 

Here, we want to create a knowledge graph for Frederick III. To achieve this, simply execute:

```
python construct_kg.py -itinerary_file ../src/predictions/charter_locations_999999-_centers_added.json -ner_loc_file ../src/predictions/NE_locations_999999-_centers_added.json -min_ent_count 2 -emperor "Friedrich III."
```

This will write a file containing tab-separated triples into the directory knowledge\_graphs. For further analyses or changes please write your own scripts or load the files into graph visualization and analyses platforms such as [Gephi](https://gephi.org/) or [Cytoscape](https://cytoscape.org/).


