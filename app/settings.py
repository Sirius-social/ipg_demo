import os
import logging

import sirius_sdk
from fastapi.templating import Jinja2Templates


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


ACTOR1 = {
  "server_uri": "https://agents.socialsirius.com",
  "credentials": "f4WDZVlHF7mi81PyYBjHa2asdLTR6g0oF2+tBwngVs9e3CWqvHh8zl2xSzbBh8nGrZhYw+bgj47l/Hbv8WnGGWaN/VOMAiEOnkkBnnL/X54=".encode(),
  "p2p": sirius_sdk.P2PConnection(
    their_verkey="CBDQGq1pYieQrHkmV3xh6hAtvP5oi2Ka59wq3ZXykpjp",
    my_keys=(
      "7uQV45RGcF1z21TcXVEytoPPV97RJW2Z3B1F8x9FFy68",
      "5uYCJpsRXCycJ2Rk9w6j82ASoGTbM2LVTFCdJrFDLbqFJm4Y3MVhk7mAzp7teTgdi4GFaJoPXqt2HcK32WynuwvG"
    )
  )
}


ACTOR2 = {
  "server_uri": "https://agents.socialsirius.com",
  "credentials": "f4WDZVlHF7mi81PyYBjHa2asdLTR6g0oF2+tBwngVs9e3CWqvHh8zl2xSzbBh8nGpb1ahFtVLLGplGLn0oKeU2aN/VOMAiEOnkkBnnL/X54=".encode(),
  "p2p": sirius_sdk.P2PConnection(
    their_verkey="7qZQS2JHnT5i1UzRu6MsUaz6Z6UHGa4jDHXNHG5rBKps",
    my_keys=(
      "2rHCLR8NCRAsxZUdmCRg53s6vAix3QSDRhbFUeU423pE",
      "2C3CFoLZ7LHTbfqZyTjaLjLwzxqLSJTnQhQ8quXoLAdYpk4T1RS67Ue54DzBa1Ez2i2hcaiEjrT3gMUgfKQgxKxE"
    )
  )
}


ACTOR3 = {
    "server_uri": "https://agents.socialsirius.com",
    "credentials": "f4WDZVlHF7mi81PyYBjHa2asdLTR6g0oF2+tBwngVs9e3CWqvHh8zl2xSzbBh8nGBxsehWYTfDYgxmFnvfL9q2aN/VOMAiEOnkkBnnL/X54=".encode(),
    "p2p": sirius_sdk.P2PConnection(
        their_verkey="93yjXvesU2w6Sj5Ei3P9GYyGLTMPg7DjT7sqDeBDFW3g",
        my_keys=(
          "Cu1LgDJba7W39vTaHXjeniqMXmFcFFsg6WL5y8QyTNkn",
          "5B9G5BBTHfyCKw4HRokDd8NfQCbTyrBP3a1s8f3JJH3dYQ4C48xiRzch7Wb3g7MFmycjHxUxBFsnfhUpAiqr6yvN"
        )
    )
}
