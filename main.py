import os
import scheduler
import time

from config_reader import read_config
from web.app import webapp, APP_VERSION
from datastore import add_log_entry, LogCategory

def main():
    print('')
    print(f'=== PriceKeeper [v{APP_VERSION}] ===')
    print('')

    print('Reading config...')
    cfg = read_config()

    print('Scheduling jobs...')
    scheduler.init_jobs(cfg)

    port = 9600
    if os.getenv('PKAPP_PORT') is not None:
        tmp_port = os.getenv('PKAPP_PORT')
        try:
            tmp_port = int(tmp_port)
            if tmp_port < 1 or tmp_port > 65535:
                raise Exception('Port out of range.')
            port = tmp_port
        except:
            print(f"Warning: specified port number in environment variables ({tmp_port}) is not a valid port number.")

    listen_addr = '0.0.0.0'
    if os.getenv('PKAPP_LISTEN') is not None:
        tmp_listen = os.getenv('PKAPP_LISTEN')
        if len(tmp_listen) and (tmp_listen.count('.') == 3 or tmp_listen.count(':') >= 2):
            listen_addr = tmp_listen.strip()

    debug_flag = False
    if os.getenv('PKAPP_DEBUG') is not None:
        tmp_debug = os.getenv('PKAPP_DEBUG')
        if len(tmp_debug) and (tmp_debug.lower().strip() == 'true' or tmp_debug.lower().strip() == '1'):
            debug_flag = True

    add_log_entry(cfg, LogCategory.CAT_SYSTEM, f"PriceKeeper v{APP_VERSION} has started (Listen={listen_addr}) (Port={port}){(' (Debug=True)' if debug_flag else '')}")

    print(f"Running on: http://{('127.0.0.1' if listen_addr == '0.0.0.0' else listen_addr)}:{port}")
    try:
        webapp().run(listen_addr, port, debug=debug_flag)
    except SystemExit as se:
        add_log_entry(cfg, LogCategory.CAT_SYSTEM, f"PriceKeeper v{APP_VERSION} is shutting down.")


if __name__ == '__main__':
    main()
