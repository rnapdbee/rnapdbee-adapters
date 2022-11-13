#! /usr/bin/env python

from __future__ import annotations

import orjson
from flask import Blueprint, request

from adapters.visualization.weblogo_ import WeblogoDrawer
from adapters.visualization.rchie import RChieDrawer
from adapters.visualization.pseudoviewer import PseudoViewerDrawer
from adapters.visualization.rnapuzzler import RNAPuzzlerDrawer
from adapters.tools.utils import content_type, svg_response
from adapters.visualization.model import ModelMulti2D

server = Blueprint('visualization', __name__)

# Weblogo drawer routes


@server.route('/weblogo', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_weblogo():
    model = ModelMulti2D.from_dict(orjson.loads(request.data))
    return WeblogoDrawer().visualize(model)


@server.route('/rchie', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_rchie():
    # TODO: RchieDrawer
    # -- Reminder --
    # paired residues on separate strands -> 1 image
    # all pairs within strand -> N images
    # input: structure
    model = ModelMulti2D.from_dict(orjson.loads(request.data))
    return RChieDrawer().visualize(model)


@server.route('/pseudoviewer', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_pseudoviewer():
    # TODO: PseudoViewerDrawer
    # -- Reminder --
    # same as RChie and moreover
    # strands must be numbered, pseudoknots and missing resiudes must be removed
    # input: sequence, structure
    model = ModelMulti2D.from_dict(orjson.loads(request.data))
    return PseudoViewerDrawer().visualize(model)


@server.route('/rnapuzzler', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_rnapuzzler():
    # TODO: RNAPuzzlerDrawer
    # -- Reminder --
    # N images (?) Pseduknots and missing residues not supported (?)
    # output is called 'rna.svg' if fasta header not passed
    # input: seuquence, structure
    model = ModelMulti2D.from_dict(orjson.loads(request.data))
    return RNAPuzzlerDrawer().visualize(model)


@server.route('/rnaglib', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_rnaglib():
    # TODO: RNAglibDrawer
    # -- Reminder --
    # Input: graph from mmCIF (?)
    # Local mmCIF requires x3dna-dssr with license (?)
    # Cannot show and save file, matplotlib problem (?)
    # Latex is required
    # Package is quite heavy (CUDA, torch)
    return NotImplementedError()
