#! /usr/bin/env python

from flask import Flask

from adapters.routes.analysis import server as analysis
from adapters.routes.conversion import server as conversion
from adapters.routes.filtering import server as filtering

app = Flask(__name__)

app.register_blueprint(analysis)
app.register_blueprint(conversion)
app.register_blueprint(filtering)

if __name__ == '__main__':
    app.run(debug=True)
