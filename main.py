import scheduler
import time

from config_reader import read_config
from web.app import webapp, APP_VERSION


def main():
    print('')
    print(f'=== PriceKeeper [v{APP_VERSION}] ===')
    print('')

    print('Reading config...')
    cfg = read_config()

    print('Scheduling jobs...')
    scheduler.init_jobs(cfg)

    print('Running...')
    webapp().run("0.0.0.0", 9600, debug=False)


if __name__ == '__main__':
    main()
