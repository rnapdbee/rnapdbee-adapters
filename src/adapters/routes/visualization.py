#! /usr/bin/env python

from __future__ import annotations

import orjson
from flask import Blueprint, request

from adapters.visualization.weblogo_ import WeblogoDrawer
from adapters.visualization.rchie import RChieDrawer
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
    model = ModelMulti2D.from_dict(orjson.loads(request.data))
    return RChieDrawer().visualize(model)
