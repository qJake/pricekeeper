from scheduler import get_jobs, run_now, init_jobs
from datastore import get_price_summary, get_price_history
from config_reader import read_config
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


APP_VERSION = '1.6'


def webapp():

    app = Flask(__name__)

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

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

        if len(prices):
            low = min(p['y'] for p in prices)
            high = max(p['y'] for p in prices)
            current = sorted((p for p in prices), key=lambda d: d['x'], reverse=True)[0]['y']
        else:
            low = 0.0
            high = 0.0
            current = 0.0

        vm = vm | {
            'priceJson': json.dumps(prices),
            'low': low,
            'high': high,
            'current': current
        }
        return render_template("graph.html", context=vm)

    @app.route("/refresh")
    def refresh():
        print('Running all jobs now...')
        run_now()
        print('Completed.')
        return redirect("/")

    @app.route("/reload")
    def reload():
        print('Reloading config...')
        config = read_config()
        init_jobs(config)
        print(f'Reloaded {len(config.rules)} rule(s).')
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

    @app.route("/_health")
    def healthCheck():
        return render_template("_health.html")

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
