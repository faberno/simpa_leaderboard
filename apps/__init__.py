# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
import pytz
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()

tz = pytz.timezone("Europe/Berlin")
hackathon_start = os.getenv('HACKATHON_START')
hackathon_start = datetime.strptime(hackathon_start, '%d-%m-%Y')
hackathon_start = hackathon_start.replace(tzinfo=tz)
github_token = os.getenv('GITHUB_TOKEN')
repo_name = os.getenv('GITHUB_REPO')


def date_after_start(date):
    """Is date after hackathon start?"""
    return date > hackathon_start

def truncate_string(value, length=100):
    if len(value) > length:
        return value[:length] + '...'
    return value

def register_extensions(app):
    db.init_app(app)
    # login_manager.init_app(app)


def register_blueprints(app):
    # for module_name in ('authentication', 'home', 'api'):
    for module_name in ('home', ):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):
    def initialize_database():
        try:
            db.create_all()
        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e))

            # fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir,
                                                                                                          'db.sqlite3')
            print('> Fallback to SQLite ')
            db.create_all()

    initialize_database()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    app.jinja_env.globals.update(truncate_string=truncate_string)
    with app.app_context():
        configure_database(app)
    return app
