#! /usr/bin/env python

from flask import Blueprint, request

from adapters.tools import output_filter, cif_filter, pdb_filter
from adapters.tools.utils import content_type, json_response
from adapters.tools.cif_filter import fix_occupancy, leave_single_model, remove_proteins
from adapters.analysis import bpnet, fr3d_, rnapolis_
from adapters.analysis.barnaba_ import BarnabaAdapter
from adapters.analysis.mc_annotate import MCAnnotateAdapter
from adapters.analysis.rnaview import RNAViewAdapter

server = Blueprint('analysis', __name__)

# BPNet adapter routes


@server.route('/bpnet/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_bpnet_model(model):
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (leave_single_model, {'model': model}),
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
    analysis_output = bpnet.analyze(cif_content)
    filtered_analysis_output = output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@server.route('/bpnet', methods=['POST'])
def analyze_bpnet():
    return analyze_bpnet_model(1)


# FR3D adapter routes


@server.route('/fr3d/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_fr3d_model(model):
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (leave_single_model, {'model': model}),
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
    analysis_output = fr3d_.analyze(cif_content)
    filtered_analysis_output = output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@server.route('/fr3d', methods=['POST'])
def analyze_fr3d():
    return analyze_fr3d_model(1)


# BaRNAba adapter routes


@server.route('/barnaba/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_barnaba_model(model):
    pdb_content = pdb_filter.apply(request.data.decode('utf-8'), [
        (pdb_filter.leave_single_model, {'model': model}),
    ])
    analysis_output = BarnabaAdapter().analyze(pdb_content)
    filtered_analysis_output = output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@server.route('/barnaba', methods=['POST'])
def analyze_barnaba():
    return analyze_barnaba_model(1)


# MC-Annotate adapter routes


@server.route('/mc-annotate/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_mc_annotate_model(model):
    pdb_content = pdb_filter.apply(request.data.decode('utf-8'), [
        (pdb_filter.leave_single_model, {'model': model}),
    ])
    analysis_output = MCAnnotateAdapter().analyze(pdb_content)
    filtered_analysis_output = output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@server.route('/mc-annotate', methods=['POST'])
def analyze_mc_annotate():
    return analyze_mc_annotate_model(1)


# RNAView adapter routes


@server.route('/rnaview/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_rnaview_model(model):
    pdb_content = pdb_filter.apply(request.data.decode('utf-8'), [
        (pdb_filter.leave_single_model, {'model': model}),
    ])
    analysis_output = RNAViewAdapter().analyze(pdb_content)
    filtered_analysis_output = output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@server.route('/rnaview', methods=['POST'])
def analyze_rnaview():
    return analyze_rnaview_model(1)


# RNApolis adapter routes


@server.route('/rnapolis/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_rnapolis_model(model):
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (leave_single_model, {'model': model}),
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
    analysis_output = rnapolis_.analyze(cif_content, model)
    filtered_analysis_output = output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@server.route('/rnapolis', methods=['POST'])
def analyze_rnapolis():
    return analyze_rnapolis_model(1)
