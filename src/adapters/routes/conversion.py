from flask import Blueprint, request
from rnapolis.common import BpSeq

from adapters.tools import maxit
from adapters.tools.utils import content_type, plain_response

server = Blueprint("conversion", __name__)

# MAXIT tool routes


@server.route("/ensure-cif", methods=["POST"])
@content_type("text/plain")
@plain_response()
def convert_ensure_cif():
    return maxit.ensure_cif(request.data.decode("utf-8"))


@server.route("/ensure-pdb", methods=["POST"])
@content_type("text/plain")
@plain_response()
def convert_ensure_pdb():
    return maxit.ensure_pdb(request.data.decode("utf-8"))


@server.route("/bpseq2dbn", methods=["POST"])
@content_type("text/plain")
@plain_response()
def convert_bpseq2dbn():
    return str(BpSeq.from_string(request.data.decode("utf-8")).dot_bracket)
