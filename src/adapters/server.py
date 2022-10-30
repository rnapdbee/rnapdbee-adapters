#! /usr/bin/env python

from flask import Flask

from adapters.routes.analysis import server as analysis
from adapters.routes.conversion import server as conversion
from adapters.routes.filtering import server as filtering
from adapters.routes.visualization import server as visualization

app = Flask(__name__)

app.register_blueprint(analysis, url_prefix='/analysis-api/v1')
app.register_blueprint(conversion, url_prefix='/conversion-api/v1')
app.register_blueprint(filtering, url_prefix='/filtering-api/v1')
app.register_blueprint(visualization, url_prefix='/visualization-api/v1')

if __name__ == '__main__':
    app.run(debug=True)
