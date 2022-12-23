#! /usr/bin/env python

from flask import Blueprint, request

from adapters.tools.utils import content_type, json_response
from adapters.analysis import bpnet, fr3d_, rnapolis_, barnaba_, mc_annotate, rnaview
from adapters import services

server = Blueprint('analysis', __name__)

# BPNet adapter routes


@server.route('/bpnet/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_bpnet_model(model: int):
    return services.run_cif_adapter(
        bpnet.analyze,
        request.data.decode('utf-8'),
        model,
    )


@server.route('/bpnet', methods=['POST'])
def analyze_bpnet():
    return analyze_bpnet_model(1)


# FR3D adapter routes


@server.route('/fr3d/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_fr3d_model(model: int):
    return services.run_cif_adapter(
        fr3d_.analyze,
        request.data.decode('utf-8'),
        model,
    )


@server.route('/fr3d', methods=['POST'])
def analyze_fr3d():
    return analyze_fr3d_model(1)


# BaRNAba adapter routes


@server.route('/barnaba/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_barnaba_model(model: int):
    return services.run_pdb_adapter(
        barnaba_.analyze,
        request.data.decode('utf-8'),
        model,
    )


@server.route('/barnaba', methods=['POST'])
def analyze_barnaba():
    return analyze_barnaba_model(1)


# MC-Annotate adapter routes


@server.route('/mc-annotate/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_mc_annotate_model(model: int):
    return services.run_pdb_adapter(
        mc_annotate.analyze,
        request.data.decode('utf-8'),
        model,
    )


@server.route('/mc-annotate', methods=['POST'])
def analyze_mc_annotate():
    return analyze_mc_annotate_model(1)


# RNAView adapter routes


@server.route('/rnaview/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_rnaview_model(model: int):
    return services.run_pdb_adapter(
        rnaview.analyze,
        request.data.decode('utf-8'),
        model,
    )


@server.route('/rnaview', methods=['POST'])
def analyze_rnaview():
    return analyze_rnaview_model(1)


# RNApolis adapter routes


@server.route('/rnapolis/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_rnapolis_model(model: int):
    return services.run_cif_adapter(
        rnapolis_.analyze,
        request.data.decode('utf-8'),
        model,
    )


@server.route('/rnapolis', methods=['POST'])
def analyze_rnapolis():
    return analyze_rnapolis_model(1)
