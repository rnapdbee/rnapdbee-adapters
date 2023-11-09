#! /usr/bin/env python

from __future__ import annotations

from flask import Blueprint, request

from adapters.services import run_multi_visualization_adapter, run_visualization_adapter
from adapters.tools.utils import content_type, svg_response
from adapters.visualization.pseudoviewer import PseudoViewerDrawer
from adapters.visualization.rchie import RChieDrawer
from adapters.visualization.rnapuzzler import RNAPuzzlerDrawer
from adapters.visualization.weblogo_ import WeblogoDrawer

server = Blueprint("visualization", __name__)


@server.route("/weblogo", methods=["POST"])
@content_type("application/json")
@svg_response()
def visualize_weblogo():
    return run_multi_visualization_adapter(
        WeblogoDrawer(),
        request.data,
    )


@server.route("/rchie", methods=["POST"])
@content_type("application/json")
@svg_response()
def visualize_rchie():
    return run_visualization_adapter(
        RChieDrawer(),
        request.data,
    )


@server.route("/pseudoviewer", methods=["POST"])
@content_type("application/json")
@svg_response()
def visualize_pseudoviewer():
    return run_visualization_adapter(
        PseudoViewerDrawer(),
        request.data,
    )


@server.route("/rnapuzzler", methods=["POST"])
@content_type("application/json")
@svg_response()
def visualize_rnapuzzler():
    return run_visualization_adapter(
        RNAPuzzlerDrawer(),
        request.data,
    )
