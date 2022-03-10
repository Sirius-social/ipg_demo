import json
import os
import logging

import sirius_sdk
from fastapi.templating import Jinja2Templates

from utils import load_sdk_cred_from_file, load_json_from_file


log_levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}
log_level = log_levels.get(os.getenv('LOGLEVEL', None))
if log_level:
    logging.getLogger().setLevel(log_level)
    logging.getLogger("asyncio").setLevel(log_level)


templates = Jinja2Templates(directory="templates")

URL_STATIC = '/static'

MEMCACHED = os.environ.get('MEMCACHED')
assert MEMCACHED is not None, 'You must set MEMCACHED env variable that specify memcached server address'
if ':' in MEMCACHED:
    host, port = MEMCACHED.split(':')
    MEMCACHED = host
    MEMCACHED_PORT = int(port)
else:
    MEMCACHED_PORT = 11211

assert os.environ.get('REDIS') is not None, 'You must set REDIS env variable, for example: "redis://address1,redis://address2"'
REDIS = []
for item in os.environ.get('REDIS').split(','):
    parts = item.split('://')
    if len(parts) > 1:
        scheme, address = parts[0], parts[1]
        if scheme == 'redis':
            REDIS.append(address)
    else:
        address = item
        REDIS.append(address)


# Postgres
DATABASE_HOST = os.getenv('DATABASE_HOST')
assert DATABASE_HOST is not None, 'You must set DATABASE_HOST env variable'
DATABASE_NAME = os.getenv('DATABASE_NAME')
assert DATABASE_NAME is not None, 'You must set DATABASE_NAME env variable'
DATABASE_USER = os.getenv('DATABASE_USER')
assert DATABASE_USER is not None, 'You must set DATABASE_USER env variable'
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
assert DATABASE_PASSWORD is not None, 'You must set DATABASE_PASSWORD env variable'
DATABASE_PORT = int(os.getenv('DATABASE_PORT', 5432))
TEST_DATABASE_NAME = 'test_database'

SQLALCHEMY_DATABASE_URL = \
    f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
TEST_SQLALCHEMY_DATABASE_URL = \
    f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{TEST_DATABASE_NAME}"
IS_PRODUCTION = os.getenv('PROD', None) in ['on', 'yes']


SDK = os.getenv('SDK')
if not SDK:
    raise RuntimeError('Env var SDK must be set')
SDK, extra = load_sdk_cred_from_file(SDK)

SDK_STEWARD = os.getenv('STEWARD')
if not SDK_STEWARD:
    raise RuntimeError('Env var STEWARD must be set')
js = load_json_from_file(SDK_STEWARD)
SDK_STEWARD, _ = load_sdk_cred_from_file(SDK_STEWARD)
STEWARD_DID = js['did']

DKMS_NETWORK = 'test_network'
TITLE = extra.pop('title', 'Demo Company Ltd.')
ICON = extra.pop('icon', '/static/icons/logo.png')
MASTER_SECRET_ID = extra.pop('master_secret_id')


sirius_sdk.init(**SDK)

