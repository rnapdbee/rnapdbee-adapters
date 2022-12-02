#! /usr/bin/env python

from __future__ import annotations

import orjson
from flask import Blueprint, request

from adapters.visualization.weblogo_ import WeblogoDrawer
from adapters.visualization.rchie import RChieDrawer
from adapters.visualization.pseudoviewer import PseudoViewerDrawer
from adapters.tools.utils import content_type, svg_response
from adapters.visualization.model import ModelMulti2D, Model2D

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
    model = Model2D.from_dict(orjson.loads(request.data))
    return RChieDrawer().visualize(model)


@server.route('/pseudoviewer', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_pseudoviewer():
    model = Model2D.from_dict(orjson.loads(request.data))
    return PseudoViewerDrawer().visualize(model)


@server.route('/rnapuzzler', methods=['POST'])
@content_type('application/json')
@svg_response()
def visualize_rnapuzzler():
    # TODO: RNAPuzzlerDrawer
    # progress: 30%
    # problem: wait for stdin in some cases casuing timeout
    return NotImplementedError()
