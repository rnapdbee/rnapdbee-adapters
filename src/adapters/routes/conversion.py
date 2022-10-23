from flask import Blueprint, request

from adapters.tools import maxit
from adapters.tools.utils import content_type, plain_response

server = Blueprint('conversion', __name__)

# MAXIT tool routes


@server.route('/convert/ensure-cif', methods=['POST'])
@content_type('text/plain')
@plain_response()
def convert_ensure_cif():
    return maxit.ensure_cif(request.data.decode('utf-8'))


@server.route('/convert/ensure-pdb', methods=['POST'])
@content_type('text/plain')
@plain_response()
def convert_ensure_pdb():
    return maxit.ensure_pdb(request.data.decode('utf-8'))
