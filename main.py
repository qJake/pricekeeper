import scheduler
import time

from config_reader import read_config
from web.app import webapp

def main():
    print('Reading config...')
    cfg = read_config()

    print('Scheduling jobs...')
    scheduler.init_jobs(cfg)

    print('Running...')
    webapp().run("0.0.0.0", 6900, debug=False)

    # Not needed since the webserver spins itself
    # while True:
    #     time.sleep(60)


if __name__ == '__main__':
    main()
