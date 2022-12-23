#! /usr/bin/env python

from flask import Blueprint, request

from adapters.tools import cif_filter
from adapters.tools.utils import content_type, plain_response
from adapters.tools.cif_filter import remove_proteins, fix_occupancy

server = Blueprint('filtering', __name__)

# Cif filter routes


@server.route('/filter', methods=['POST'])
@content_type('text/plain')
@plain_response()
def filter_cif():
    return cif_filter.apply(request.data.decode('utf-8'), [
        (remove_proteins, {}),
        (fix_occupancy, {}),
    ])
