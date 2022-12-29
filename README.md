# RNApdbee-adapters
![workflow](https://github.com/rnapdbee/rnapdbee-adapters/actions/workflows/docker.yml/badge.svg)

## Description

The project contains adapters for various external tools used by RNApdbee 3.0. It can be divided into three main parts described below.

### RNA analysis tools

- [baRNAba](https://github.com/srnas/barnaba)
- [BPNET](https://github.com/computational-biology/bpnet)
- [fr3d-python](https://github.com/BGSU-RNA/fr3d-python)
- [MC-Annotate](https://github.com/major-lab/MC-Annotate)
- [RNApolis](https://github.com/tzok/rnapolis-py)
- [RNAView](http://ndbserver.rutgers.edu/ndbmodule/services/download/rnaview.html)

### File conversion tools
- [MAXIT](https://sw-tools.rcsb.org/apps/MAXIT/index.html)

### RNA visualization tools
- [PseudoViewer](http://pseudoviewer.inha.ac.kr/)
- [RChie](https://www.e-rna.org/r-chie/)
- [RNApuzzler](https://www.tbi.univie.ac.at/RNA/RNAplot.1.html)
- [WebLogo](https://weblogo.threeplusone.com/)

### Other meaningful software
- [Ubuntu 22.04](https://ubuntu.com/)
- [Python 3.10](https://www.python.org/)
- [R](https://www.r-project.org/)
- [IronPython](https://ironpython.net/)
- [Docker](https://ironpython.net/)
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

## Building

```
$ ./build.sh
```

## Usage

```
$ docker run -p 8000:8000 rnapdbee-adapter-server
```

In another terminal:

```
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analyze/bpnet
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analyze/fr3d
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/analyze/barnaba
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/convert/ensure-cif
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/convert/ensure-pdb
```

## Example

The data model can be understood by looking at [src/adapters/model.py](src/adapters/model.py). An example output JSON produced by BPNET for 1EHZ structure is available in [1ehz.json](1ehz.json) file.
