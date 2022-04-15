#! /usr/bin/env python
from http import HTTPStatus

import orjson
from flask import Flask, Response, request

from adapters import bpnet, fr3d_, maxit

app = Flask(__name__)


@app.route('/bpnet', methods=['POST'])
def bpnet_handler():
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    cif_or_pdb = request.data.decode('utf-8')
    cif = maxit.ensure_cif(cif_or_pdb)
    structure = bpnet.analyze(cif)
    return Response(response=orjson.dumps(structure).decode('utf-8'), status=HTTPStatus.OK, mimetype='application/json')


@app.route('/fr3d', methods=['POST'])
def fr3d_handler():
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    cif_or_pdb = request.data.decode('utf-8')
    cif = maxit.ensure_cif(cif_or_pdb)
    structure = fr3d_.analyze(cif)
    return Response(response=orjson.dumps(structure).decode('utf-8'), status=HTTPStatus.OK, mimetype='application/json')


@app.route('/maxit', methods=['POST'])
def maxit_handler():
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    cif = maxit.ensure_cif(request.data.decode('utf-8'))
    return Response(response=cif, status=HTTPStatus.OK, mimetype='text/plain')


if __name__ == '__main__':
    app.run(debug=True)
