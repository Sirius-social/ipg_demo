import os
import json
from typing import Optional, List, Dict, Union, Tuple

import sirius_sdk


def load_json_from_file(path: str) -> Union[list, dict]:
    if not os.path.isfile(path):
        raise RuntimeError(f'SDK file {path} does not exists')
    with open(path, 'rb') as f:
        content = f.read()
        js = json.loads(content)
    return js


def load_sdk_cred_from_file(path: str) -> (dict, dict):
    """Return parsed SDK cred, extra arguments"""

    js = load_json_from_file(path)
    sdk, extra = {}, {}
    expected_fields = ['credentials', 'p2p', 'server_uri']
    for field in expected_fields:
        if field in js.keys():
            sdk[field] = js.pop(field)
        else:
            raise RuntimeError(f'Expected field "{field}" does not exists!')
    extra = js

    if type(sdk['credentials']) is str:
        sdk['credentials'] = sdk['credentials'].encode()
    if type(sdk['p2p']) is dict:
        sdk['p2p'] = sirius_sdk.P2PConnection(
            their_verkey=sdk['p2p']['their_verkey'],
            my_keys=tuple(sdk['p2p']['my_keys'])
        )
    return sdk, extra
