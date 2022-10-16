#! /usr/bin/env python

import tempfile

import rnapolis.annotator
import rnapolis.parser
from flask import Flask, request

from adapters import (analysis_output_filter, bpnet, cif_filter, fr3d_, maxit,
                      pdb_filter)
from adapters.barnaba_ import BarnabaAdapter
from adapters.cif_filter import (fix_occupancy, leave_single_model,
                                 remove_proteins)
from adapters.mc_annotate import MCAnnotateAdapter
from adapters.rnaview import RNAViewAdapter
from adapters.utils import content_type, json_response, plain_response

app = Flask(__name__)

# BPNet adapter routes


@app.route('/analyze/bpnet/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_bpnet_model(model):
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (leave_single_model, {'model': model}),
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
    analysis_output = bpnet.analyze(cif_content)
    filtered_analysis_output = analysis_output_filter.apply(analysis_output, [
        (analysis_output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@app.route('/analyze/bpnet', methods=['POST'])
def analyze_bpnet():
    return analyze_bpnet_model(1)


@app.route('/analyze/<int:model>', methods=['POST'])
def analyze_model(model):
    return analyze_bpnet_model(model)


@app.route('/analyze', methods=['POST'])
def analyze():
    return analyze_model(1)


# FR3D adapter routes


@app.route('/analyze/fr3d/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_fr3d_model(model):
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (leave_single_model, {'model': model}),
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
    analysis_output = fr3d_.analyze(cif_content)
    filtered_analysis_output = analysis_output_filter.apply(analysis_output, [
        (analysis_output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@app.route('/analyze/fr3d', methods=['POST'])
def analyze_fr3d():
    return analyze_fr3d_model(1)


# BaRNAba adapter routes


@app.route('/analyze/barnaba/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_barnaba_model(model):
    pdb_content = pdb_filter.apply(request.data.decode('utf-8'), [
        (pdb_filter.leave_single_model, {'model': model}),
    ])
    analysis_output = BarnabaAdapter().analyze(pdb_content)
    filtered_analysis_output = analysis_output_filter.apply(analysis_output, [
        (analysis_output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@app.route('/analyze/barnaba', methods=['POST'])
def analyze_barnaba():
    return analyze_barnaba_model(1)


# MC-Annotate adapter routes


@app.route('/analyze/mc-annotate/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_mc_annotate_model(model):
    pdb_content = pdb_filter.apply(request.data.decode('utf-8'), [
        (pdb_filter.leave_single_model, {'model': model}),
    ])
    analysis_output = MCAnnotateAdapter().analyze(pdb_content)
    filtered_analysis_output = analysis_output_filter.apply(analysis_output, [
        (analysis_output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@app.route('/analyze/mc-annotate', methods=['POST'])
def analyze_mc_annotate():
    return analyze_mc_annotate_model(1)


# RNAView adapter routes


@app.route('/analyze/rnaview/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_rnaview_model(model):
    pdb_content = pdb_filter.apply(request.data.decode('utf-8'), [
        (pdb_filter.leave_single_model, {'model': model}),
    ])
    analysis_output = RNAViewAdapter().analyze(pdb_content)
    filtered_analysis_output = analysis_output_filter.apply(analysis_output, [
        (analysis_output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@app.route('/analyze/rnaview', methods=['POST'])
def analyze_rnaview():
    return analyze_rnaview_model(1)


# RNApolis adapter routes


@app.route('/analyze/rnapolis/<int:model>', methods=['POST'])
@content_type('text/plain')
@json_response()
def analyze_rnapolis_model(model):
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (leave_single_model, {'model': model}),
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])

    with tempfile.NamedTemporaryFile('w+') as cif_file:
        cif_file.write(cif_content)
        cif_file.seek(0)
        tertiary_structure = rnapolis.parser.read_3d_structure(cif_file, model)

    secondary_structure = rnapolis.annotator.extract_secondary_structure(tertiary_structure, model)
    filtered_analysis_output = analysis_output_filter.apply(secondary_structure, [
        (analysis_output_filter.remove_duplicate_pairs, {}),
    ])
    return filtered_analysis_output


@app.route('/analyze/rnapolis', methods=['POST'])
def analyze_rnapolis():
    return analyze_rnapolis_model(1)


# MAXIT tool routes


@app.route('/convert/ensure-cif', methods=['POST'])
@content_type('text/plain')
@plain_response()
def convert_ensure_cif():
    cif = maxit.ensure_cif(request.data.decode('utf-8'))
    return cif


@app.route('/convert/ensure-pdb', methods=['POST'])
@content_type('text/plain')
@plain_response()
def convert_ensure_pdb():
    pdb = maxit.ensure_pdb(request.data.decode('utf-8'))
    return pdb


# Cif filter routes


@app.route('/filter', methods=['POST'])
@content_type('text/plain')
@plain_response()
def filter_cif():
    cif_content = cif_filter.apply(request.data.decode('utf-8'), [
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
    return cif_content


if __name__ == '__main__':
    app.run(debug=True)
