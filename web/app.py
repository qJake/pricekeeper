import json
import os
import sys
import inspect
import base64

from io import BytesIO
from types import SimpleNamespace
from typing import Tuple
from flask import Flask, render_template, request, redirect, Response
from PIL import Image

from scheduler import get_jobs, run_all, run, init_jobs
from datastore import get_price_summary, get_price_history, get_log_entries, add_log_entry, LogCategory, get_sparkline, get_sparklines
import config_reader as store
from utils import name_cat_mapping, get_datetime_from_rowkey_secs


# Parent directory pull
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)


APP_VERSION = '1.17'


def webapp():

    app = Flask(__name__)

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    def get_vm(name: str = None) -> Tuple[SimpleNamespace, dict]:
        config = store.read_config()
        name_to_category = name_cat_mapping(config)

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
        itemSummary = get_price_summary(config, list(set(r.name for r in config.rules)))
        sparks = get_sparklines(config)
        sparks = sparks if sparks is not None else {}

        vm = vm | {
            'prices': itemSummary,
            'headers': list(set(i['category'] for i in itemSummary)),
            'sparks': sparks,
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
        config = store.read_config()
        args = request.args.to_dict()
        if 'name' in args and len(args['name'].strip()):
            print(f"Running job {args['name']}...")
            add_log_entry(config, LogCategory.CAT_JOBS, f"User requested {args['name']} job to run...")
            run(args['name'])
            add_log_entry(config, LogCategory.CAT_JOBS, 'Job has been queued.')
            print('Queued.')
        else:
            print('Running all jobs now...')
            add_log_entry(config, LogCategory.CAT_JOBS, 'User requested all jobs to run. Starting all jobs...')
            run_all()
            add_log_entry(config, LogCategory.CAT_JOBS, 'All jobs have been queued.')
            print('Queued.')
        return redirect("/")

    @app.route("/reload")
    def reload():
        print('Reloading config...')
        config = store.read_config()
        init_jobs(config)
        add_log_entry(config, LogCategory.CAT_SYSTEM, 'User requested a configuration reload.')
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
            add_log_entry(store.read_config(), LogCategory.CAT_SYSTEM, f"Unable to save rules because one or more validation errors occurred.", "\r\n".join(cfg_err.errors))
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

    @app.route("/logs")
    def logs():
        config, vm = get_vm()
        args = request.args.to_dict()
        if 'n' in args:
            logs = get_log_entries(config, int(args['n']))
        else:
            logs = get_log_entries(config)

        log_list = []        
        for l in logs:
            l['DateTime'] = get_datetime_from_rowkey_secs(int(l['RowKey']), 1000)
            log_list.append(l)
        
        vm = vm | {
            'logs': log_list,
            'nav': 'logs'
        }
        return render_template("logs.html", context=vm)


    @app.route("/_health")
    def healthCheck():
        return render_template("_health.html")

    @app.route('/spark.png')
    def sparkline():
        config = store.read_config()
        args = request.args.to_dict()
        if 'name' in args:
            spark = get_sparkline(config, args['name'])
            if spark is not None:
                return Response(base64.b64decode(spark), mimetype='image/png')
            return empty_png()
        else:
            return empty_png()
        
    def empty_png():
        # Create a 1x1 transparent image
        img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))

        # Save the image to a buffer
        buf = BytesIO()
        img.save(buf, format='png')
        buf.seek(0)

        # Return the image as a response
        return Response(buf.read(), mimetype='image/png')

    return app
