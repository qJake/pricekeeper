import json
import os
import sys
import inspect

from types import SimpleNamespace
from typing import Tuple
from flask import Flask, render_template, request, redirect

# Parent directory pull
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from config_reader import read_config
from datastore import get_price_summary, get_price_history
from scheduler import get_jobs, run_now, init_jobs

APP_VERSION = '1.1'

def webapp():

    app = Flask(__name__)

    @app.route("/")
    def home():
        config, vm = get_vm()
        itemSummary = get_price_summary(config, (r.name for r in config.rules))

        vm = vm | {
            'prices': itemSummary,
            'nav': 'home'
        }
        return render_template("index.html", context=vm)


    @app.route("/graph")
    def graph():
        args = request.args.to_dict()
        if 'name' not in args or len(args['name']) == 0:
            return redirect('/error?m=Missing required parameter: name')
        name = request.args.to_dict()['name']

        config, vm = get_vm(name)
        prices = get_price_history(config, name)

        vm = vm | {
            'priceJson': json.dumps(prices)
        }
        return render_template("graph.html", context=vm)

    @app.route("/refresh")
    def refresh():
        run_now()
        return redirect("/")

    @app.route("/reload")
    def reload():
        config = read_config()
        init_jobs(config)
        return redirect("/")

    @app.route("/jobs")
    def jobs():
        config, vm = get_vm()
        vm = vm | {
            'jobs': get_jobs(),
            'nav': 'jobs'
        }
        return render_template("jobs.html", context=vm)

    @app.route("/error")
    def error():
        args = request.args.to_dict()
        if 'm' in args:
            message = args['m']
        else:
            message = None
        return render_template("error.html", context={'message': message})


    def get_vm(name: str = None) -> Tuple[SimpleNamespace, dict]:
        config = read_config()
        return config, {
            'config': config,
            'categories': list(set(r.category for r in config.rules)),
            'name': name,
            'activeCategory': next((r.category for r in config.rules if name is not None and r.name == name), None),
            'appVersion': APP_VERSION
        }

    return app