# Creating a Semantic Medieval GIS from the Regesta Imperii

This project contains the scripts to create a semantic medieval GIS from the [Regesta Imperii](http://regesta-imperii.de/en/home.html), as described [here (link to pdf)](http://www.ceur-ws.org/Vol-2723/long12.pdf).

## Instructions

### Preparation

Let's grab the geo names data base:

```
./download_geo_names.sh
```

#### Recommended additional preparations

We recommend to create a virtual python 3 environment, e.g.:

```
virtualenv -p /usr/bin/python3.7 ri-env
```

and activate it

```
source ri-env/bin/activate
```

And then we install necessary python modules:

```
pip install -r requirements.txt
```

And download an NLP model for German:

```
python -m spacy download de_core_news_lg
```

### Pipelines


#### Fast way

This is a short cut that only runs the resolution based on some files which we already processed. 
It uses the RI snapshot which we used (with a simple downlad, i.e. no time-consuming crawling is required).
It also uses a ready-made place-name candidate map and the NLP pre-processed files (only a download is required, see below).

To get the RI snapshot which we used already in nice json format (together with the result of NER and Dependency parsing) and to get the result of NER and Dependency parsing and candidate extractions:

```
./download_intermediate_files.sh
```

run place resolutions based on downloaded preprocessed files

```
./only_resolve_pipeline.sh
```

The predictions will be written in src/predictions/.

#### Slow way

Here, we do everything **from scratch**. 
We first get the latest RI-snapshot (the corpus is continually growing).
Then we convert it to json format and run the full resolution, which involves 
the creation of the place-name candidate map via Levenshtein distance as another time-consuming preliminary step,
and time-consuming NLP preprocessing.
Only after these steps, which may require a few days,  we run the actual resolution

to download the latest ri-snapshot and do the conversion to json (*approx 3 days*):

```
cd ri-crawler
java -jar regestCrawler-v02.jar 
cd src
python regests_to_json.py
```

Afterwards run the full pipeline

```
./full_pipeline.sh
```

which will take *approx 3 days* (for the geo data base search with levenshtein distance) plus *1.5 days* for the resolution with two bootstrapping iterations.

Alternatively, you can try the whole process with toy data first

```
./test_small_full_pipeline.sh
```

## Other

### Fully processed automatic annotations

You can download this [zip file](https://www.cl.uni-heidelberg.de/~opitz/data/rigeo/final_outputs.zip), in which you find
1. place predictions for charter origins
2. place predictions for named entities occuring in the charter texts and (new) **their titles** (queen, bishop, monk, ...), along with some NLP annotations

### what else can you do with this project?

By using the individual building blocks of this project, you can do specific things: For example, 
- you can get up-to-date RI-snapshots in xml (see ri-crawler), scripts to convert the xml files into nicer json 
- do dependency parsing and NER (see src/ and `src/data_helpers.py`)
- scripts to plot heatmaps (see vis/)
- use example scripts to create spatially grounded semantic medieval KGs (see more-tools/)
- and more, also see below

We recommend peaking into the bash script `full_pipeline.sh` to get an overview over some central steps.

### what can be done to improve this project?

- On a technical level, we would like to make the code run faster (parallelization?). 
- On a prediction performance level we would like to increase the accuracy of the resolutions. 
    - the place name matching may be improved 
    - the candidate coverage could be increased, by using additional geo data bases. 
    - the traveling cost formula may be improved significantly or 
    - place prediction may be addressed with a compeltely different technique. 
    - it would be also nice to "type" the named entities (for example into monasteries, cities, persons, etc. since using spacy NER alone is too coarse grained for many purposes)
- write analyses scripts that, e.g., compare emperors w.r.t. to their geo-spatial ruling habits or construct/analyze knowledge graphs

### Citation

Bib:

```
@inproceedings{DBLP:conf/chr/Opitz20,
  author    = {Juri Opitz},
  editor    = {Folgert Karsdorp and
               Barbara McGillivray and
               Adina Nerghes and
               Melvin Wevers},
  title     = {Automatic Creation of a Large-Scale Tempo-Spatial and Semantic Medieval
               European Information System},
  booktitle = {Proceedings of the Workshop on Computational Humanities Research {(CHR}
               2020), Amsterdam, The Netherlands, November 18-20, 2020},
  series    = {{CEUR} Workshop Proceedings},
  volume    = {2723},
  pages     = {397--419},
  publisher = {CEUR-WS.org},
  year      = {2020},
  url       = {http://ceur-ws.org/Vol-2723/long12.pdf},
  biburl    = {https://dblp.org/rec/conf/chr/Opitz20.bib},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}
```

APA:

`Juri Opitz (2020). Automatic Creation of a Large-Scale Tempo-Spatial and Semantic Medieval European Information System. In Proceedings of the Workshop on Computational Humanities Research (CHR 2020), Amsterdam, The Netherlands, November 18-20, 2020 (pp. 397–419). CEUR-WS.org.`
