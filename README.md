# RNApdbee-adapters

## Description

The project contains adapters for various external tools used by RNApdbee.

Currently, it supports:

- [BPNET](https://github.com/computational-biology/bpnet)
- [fr3d-python](https://github.com/BGSU-RNA/fr3d-python)
- [MAXIT](https://sw-tools.rcsb.org/apps/MAXIT/index.html)

Each tool has a standalone Docker image to use.

There is also one image which contains an HTTP server providing these endpoints:

- `POST /bpnet`, accepting PDB or PDBx/mmCIF data as `text/plain` and producing `application/json` thanks to BPNET
- `POST /fr3d`, accepting PDB or PDBx/mmCIF data as `text/plain` and producing `application/json` thanks to fr3d-python
- `POST /maxit`, accepting PDB or PDBx/mmCIF data as `text/plain` and producing PDBx/mmCIF as `text/plain` thanks to MAXIT

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
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/convert/ensure-cif
$ curl -H 'Content-Type: text/plain' --data-binary @/path/to/input http://localhost:8000/convert/ensure-pdb
```

## Example

The data model can be understood by looking at [src/adapters/model.py](src/adapters/model.py). An example output JSON produced by BPNET for 1EHZ structure is available in [1ehz.json](1ehz.json) file.
