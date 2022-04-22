#! /usr/bin/env python
from http import HTTPStatus

import orjson
from flask import Flask, Response, request

from adapters import bpnet, fr3d_, maxit, cif_filter

app = Flask(__name__)


@app.route('/analyze/bpnet/<int:model>', methods=['POST'])
def analyze_bpnet_model(model):
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    cif_content = cif_filter.filter_by_model(request.data.decode('utf-8'), model)
    structure = bpnet.analyze(cif_content)
    return Response(response=orjson.dumps(structure).decode('utf-8'), status=HTTPStatus.OK, mimetype='application/json')


@app.route('/analyze/bpnet', methods=['POST'])
def analyze_bpnet():
    return analyze_bpnet_model(1)


@app.route('/analyze/<int:model>', methods=['POST'])
def analyze_model(model):
    return analyze_bpnet_model(model)


@app.route('/analyze/fr3d/<int:model>', methods=['POST'])
def analyze_fr3d_model(model):
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    cif_content = cif_filter.filter_by_model(request.data.decode('utf-8'), model)
    structure = fr3d_.analyze(cif_content)
    return Response(response=orjson.dumps(structure).decode('utf-8'), status=HTTPStatus.OK, mimetype='application/json')


@app.route('/analyze/fr3d', methods=['POST'])
def analyze_fr3d():
    return analyze_fr3d_model(1)


@app.route('/analyze', methods=['POST'])
def analyze():
    return analyze_model(1)


@app.route('/convert/ensure-cif', methods=['POST'])
def convert_ensure_cif():
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    cif = maxit.ensure_cif(request.data.decode('utf-8'))
    return Response(response=cif, status=HTTPStatus.OK, mimetype='text/plain')


@app.route('/convert/ensure-pdb', methods=['POST'])
def convert_ensure_pdb():
    if request.headers['Content-Type'] != 'text/plain':
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    pdb = maxit.ensure_pdb(request.data.decode('utf-8'))
    return Response(response=pdb, status=HTTPStatus.OK, mimetype='text/plain')


if __name__ == '__main__':
    app.run(debug=True)
