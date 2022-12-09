import json
import os
import sys
import inspect
from types import SimpleNamespace
from typing import Tuple
from flask import Flask, render_template, request, redirect

from scheduler import get_jobs, run_now, init_jobs
from datastore import get_price_summary, get_price_history
import config_reader as store


# Parent directory pull
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)


APP_VERSION = '1.10'


def webapp():

    app = Flask(__name__)

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    def get_vm(name: str = None) -> Tuple[SimpleNamespace, dict]:
        config = store.read_config()
        
        name_to_category = {r.name: r.category for r in config.rules}
        return config, {
            'config': config,
            'categories': list(set(r.category for r in config.rules)),
            'name': name,
            'activeCategory': name_to_category.get(name, None),
            'appVersion': APP_VERSION
        }

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

        # Get the view model
        config, vm = get_vm(name)

        # Get price history
        prices = get_price_history(config, name)

        # Get min/max/current
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
        config = store.read_config()
        init_jobs(config)
        print(f'Reloaded {len(config.rules)} rule(s).')
        return redirect("/")

    @app.route("/editrules")
    def editrules():
        _, vm = get_vm()
        vm = vm | {
            'rules': store.get_yaml_rules(),
            'templates': store.get_yaml_templates(),
            'success': b'success=1' in request.query_string,
            'error': b'error=1' in request.query_string
        }
        return render_template("editrules.html", context=vm)

    @app.route("/editrules/save", methods=['POST'])
    def saverules():
        new_rules = store.yaml_to_dict(request.form['newRules'])
        config = store.read_config_dict(True)
        config['rules'] = new_rules
        try:
            store.write_config_dict(config)
        except store.ConfigValidationException as cfg_err:
            print(f"Error validating config:")
            for e in cfg_err.errors:
                print(f"  {e}")
            return redirect("/editrules?error=1")

        new_config = store.read_config()
        init_jobs(new_config)
        return redirect("/editrules?success=1")

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

    return app
