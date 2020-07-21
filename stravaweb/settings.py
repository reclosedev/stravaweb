import os
import yaml


def read_config():
    config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'etc'))
    with open(os.path.join(config_dir, 'base_config.yaml')) as fp:
        config = yaml.safe_load(fp)
    with open(os.path.join(config_dir, 'config.yaml')) as fp:
        overrides = yaml.safe_load(fp)
    config['config'].update(overrides['config'])
    return config['config']


config = read_config()

DEBUG = config['debug']
DB_URL = config['db_url']
COOKIES_PATH = config['cookies_path']
CLUBS = config['clubs']
CREDENTIALS = config['credentials']
