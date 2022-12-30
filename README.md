# RNApdbee-adapters
![workflow](https://github.com/rnapdbee/rnapdbee-adapters/actions/workflows/docker.yml/badge.svg)

## Description

The project contains adapters for various external tools used by RNApdbee 3.0. It can be divided into three main parts described below.

### RNA analysis tools
These tools make RNA structure annotation.

- [baRNAba](https://github.com/srnas/barnaba)
- [BPNET](https://github.com/computational-biology/bpnet)
- [fr3d-python](https://github.com/BGSU-RNA/fr3d-python)
- [MC-Annotate](https://github.com/major-lab/MC-Annotate)
- [RNApolis](https://github.com/tzok/rnapolis-py)
- [RNAView](http://ndbserver.rutgers.edu/ndbmodule/services/download/rnaview.html)

### File conversion tools
This tool converts `PDB` to `PDBx/mmCIF` and vice versa.

- [MAXIT](https://sw-tools.rcsb.org/apps/MAXIT/index.html)

### RNA visualization tools
These tools make 2D RNA visualization in `SVG` format.

- [PseudoViewer](http://pseudoviewer.inha.ac.kr/)
- [RChie](https://www.e-rna.org/r-chie/)
- [RNApuzzler](https://www.tbi.univie.ac.at/RNA/RNAplot.1.html)
- [WebLogo](https://weblogo.threeplusone.com/)

## Installation
Make sure you have [Docker](https://www.docker.com/) installled. 

In project root directory type the following command to build the docker image:

```
DOCKER_BUILDKIT=1 docker build --target server --tag rnapdbee-adapters-image:latest . 
```

Finally create and start docker container:

```
docker run -p 8000:80 --name rnapdbee-adapters-container rnapdbee-adapters-image:latest
```

Now API should be available trough:
```
http://localhost:8000
```

## Usage

### Analysis
Use `Content-Type: text/plain` and send `PDB` or `PDBx/mmCIF` with RNA structure ([example input](tests/files/input/2z_74.cif)). The response will be in `json` ([example output](tests/files/analysis_output/rnapolis.json)). 

```
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analysis-api/v1/barnaba
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analysis-api/v1/bpnet
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analysis-api/v1/fr3d
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analysis-api/v1/mc-annotate
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analysis-api/v1/rnapolis
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analysis-api/v1/rnaview
```

### Conversion
Use `Content-Type: text/plain` and send `PDB` or `PDBx/mmCIF` with RNA structure ([example input](tests/files/input/2z_74.cif)). The response will be in `text/plain` ([example output](tests/files/tools_output/2z_74_out.pdb)). 

```
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/conversion-api/v1/ensure-pdb
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/conversion-api/v1/ensure-cif
```

### Visualization
Use `Content-Type: application/json` and send 2D model in `json` ([example input](tests/files/input/model2D.json)). The response will be in `image/svg+xml` ([example output](tests/files/visualization_output/rchie.svg)). 

```
$ curl -H 'Content-Type: application/json' --data-binary @/path/to/input http://localhost:8000/visualization-api/v1/pseudoviewer
$ curl -H 'Content-Type: application/json' --data-binary @/path/to/input http://localhost:8000/visualization-api/v1/rchie
$ curl -H 'Content-Type: application/json' --data-binary @/path/to/input http://localhost:8000/visualization-api/v1/rnapuzzler
```

In case of consensus visualization send multi 2D model ([example input](tests/files/input/modelMulti2D.json)).

```
$ curl -H 'Content-Type: application/json' --data-binary @/path/to/input http://localhost:8000/visualization-api/v1/weblogo
```

## OpenAPI documentation
Documentation can be found [here](documentation/api/adapters-api.yml).

## Other meaningful software
The following software is used by RNApdbee adapters.

- [Ubuntu 22.04](https://ubuntu.com/)
- [Python 3.10](https://www.python.org/)
- [R](https://www.r-project.org/)
- [IronPython](https://ironpython.net/)
- [Docker](https://www.docker.com/)
- [svgcleaner](https://github.com/RazrFalcon/svgcleaner)
- [pdf2svg](https://manpages.ubuntu.com/manpages/impish/man1/pdf2svg.1.html)
- [Ghostscript](https://www.ghostscript.com/)
- [Inkscape](https://inkscape.org/)
- [Mono](https://www.mono-project.com/)
- [gunicorn](https://gunicorn.org/)
- [Flask](https://flask.palletsprojects.com/en/2.2.x/)
- [svg-stack](https://github.com/astraw/svg_stack)
- [mmcif](https://pypi.org/project/mmcif/)
- [mmcif-pdbx](https://pypi.org/project/mmcif-pdbx/)
- [lxml](https://pypi.org/project/lxml/)
- [orjson](https://pypi.org/project/orjson/)
- [dataclasses-json](https://pypi.org/project/dataclasses-json/)

## References

- **Bottaro, Sandro, et al.** "Barnaba: software for analysis of nucleic acid structures and trajectories." Rna 25.2 (2019): 219-231.
- **Roy, Parthajit, and Dhananjay Bhattacharyya.** "Contact networks in RNA: a structural bioinformatics study with a new tool." Journal of Computer-Aided Molecular Design 36.2 (2022): 131-140.
- **Sarver, Michael, et al.** "FR3D: finding local and composite recurrent structural motifs in RNA 3D structures." Journal of mathematical biology 56.1 (2008): 215-252.
- **Gendron, Patrick, Sébastien Lemieux, and François Major.** "Quantitative analysis of nucleic acid three-dimensional structures." Journal of molecular biology 308.5 (2001): 919-936.
- **Yang, Huanwang, et al.** "Tools for the automatic identification and classification of RNA base pairs." Nucleic acids research 31.13 (2003): 3450-3460.
- **Byun, Yanga, and Kyungsook Han.** "PseudoViewer3: generating planar drawings of large-scale RNA structures with pseudoknots." Bioinformatics 25.11 (2009): 1435-1437.
- **Tsybulskyi, Volodymyr, Mohamed Mounir, and Irmtraud M. Meyer.** "R-chie: A web server and R package for visualizing cis and trans RNA–RNA, RNA–DNA and DNA–DNA interactions." Nucleic Acids Research 48.18 (2020): e105-e105.
- **Wiegreffe, Daniel, et al.** "RNApuzzler: efficient outerplanar drawing of RNA-secondary structures." Bioinformatics 35.8 (2019): 1342-1349.
- **Lorenz, Ronny, et al.** "ViennaRNA Package 2.0." Algorithms for molecular biology 6.1 (2011): 1-14.
- **Crooks, Gavin E., et al.** "WebLogo: a sequence logo generator." Genome research 14.6 (2004): 1188-1190.
