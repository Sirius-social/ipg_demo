import os
import asyncio
import random
import logging
import argparse
import threading
from time import sleep
from urllib.parse import urljoin
from datetime import datetime
from collections import OrderedDict

import uvicorn
import sirius_sdk
from sirius_sdk.agent.aries_rfc.feature_0095_basic_message import Message as BasicMessage
from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

import settings
from app.settings import URL_STATIC
from operations import *


app = FastAPI()
app.mount(URL_STATIC, StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


STATIC_CFG = {
    'styles': URL_STATIC + '/admin/css/styles.css',
    'vue': URL_STATIC + '/vue.min.js',
    'axios': URL_STATIC + '/axios.min.js',
    'jquery': URL_STATIC + '/jquery-3.6.0.min.js',
    'jseditor': URL_STATIC + '/jquery.json-editor.min.js'
}


@app.get("/")
async def index(request: Request):
    my_identities = await get_my_identities()
    my_connections = await get_my_connections()
    my_schemas = await get_my_schemas()
    my_creds = await get_my_credentials()
    identities = []
    identities_labels = {}
    for item in my_identities:
        tags = item['tags']
        did = tags["did"]
        identities.append({
            'did': f'did:sov:{did}',
            'label': tags['label'],
            'inv': str(request.base_url) + tags['inv']
        })
        identities_labels[did] = tags['label']
    connections = []
    for item in my_connections:
        body = item.metadata
        body['messaging'] = {'queue': [], 'counter': 0}
        connections.append(body)
        their_did = item.their.did
        their_label = item.their.label
        identities_labels[their_did] = their_label
    schemas = []
    for item in my_schemas:
        body = item.body
        body['cred_defs'] = []
        for cred_def in item.cred_defs:
            issuer_did = cred_def.split(':')[0]
            issuer_label = identities_labels.get(issuer_did, issuer_did)
            body['cred_defs'].append({'id': cred_def, 'label': issuer_label, 'did': issuer_did})
        schemas.append(body)
    credentials = []
    for item in my_creds:
        cred = dict(**item)
        cred['issuer'] = identities_labels.get(cred['issuer_did'], None)
        credentials.append(cred)
    # WS
    ws = str(request.base_url)
    ws = ws.replace('http://', 'ws://').replace('https://', 'wss://')
    context = {
        'static': STATIC_CFG,
        'title': settings.TITLE,
        'identities': identities,
        'connections': connections,
        'schemas': schemas,
        'credentials': credentials,
        'reset_link': urljoin(str(request.base_url), '/reset'),
        'ws': ws,
        'default_proof_request': OrderedDict({
            "nonce": ''.join([random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) for _ in range(10)]),
            "name": 'Proof request',
            "version": "0.1",
            "requested_attributes": {
                'attr1_referent': {
                    "name": '<attr-name>',
                    "restrictions": {
                        "issuer_did": '<issuer-did>'
                    }

                }
            },
            "requested_predicates": {}
        })
    }
    response = templates.TemplateResponse(
        "cabinet.html",
        {
            "request": request,
            **context
        }
    )
    return response


@app.get("/reset")
async def reset_cabinet(request: Request):
    await reset()
    response = RedirectResponse(url='/')
    return response


@app.post("/")
async def action(request: Request):
    body = await request.json()
    action_ = body.get('action')
    payload_ = body.get('payload')
    try:
        if action_ == 'add-identity':
            label = payload_.get('label')
            if not label:
                raise HTTPException(status_code=400, detail="Label is Empty!")
            await create_identity(label)
        elif action_ == 'add-connection':
            inv_url = payload_.get('invitation')
            my_did = payload_.get('me')
            if ':' in my_did:
                my_did = my_did.split(':')[-1]
            my_identities = await get_my_identities(did=my_did)
            if my_identities:
                identity = my_identities[0]['tags']
                me = sirius_sdk.Pairwise.Me(did=identity['did'], verkey=identity['verkey'])
            else:
                raise HTTPException(status_code=400, detail=f"Unknown self identity with did: {my_did}")
            if not inv_url:
                raise HTTPException(status_code=400, detail="URL is Empty!")
            try:
                invitation = sirius_sdk.aries_rfc.Invitation.from_url(inv_url)
                await establish_connection_as_invitee(me, identity['label'], invitation)
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid URL structure. Check it!")
        elif action_ == 'send-message':
            their_did = payload_.get('their_did', None)
            msg = payload_.get('msg', None)
            if msg:
                collection = await get_my_connections(their_did=their_did)
                if collection:
                    p2p = collection[0]
                    await sirius_sdk.send_to(
                        message=sirius_sdk.aries_rfc.Message(content=msg),
                        to=p2p
                    )
                else:
                    raise HTTPException(status_code=400, detail="Unknown P2P")
        elif action_ == 'register-schema':
            for name, fld in payload_.items():
                if not fld:
                    raise HTTPException(status_code=400, detail=f"{name} is empty".capitalize())
            attrs = payload_['attrs']
            for i, attr in enumerate(attrs):
                name = attr.get('name')
                if not name:
                    raise HTTPException(status_code=400, detail=f"Attribute[{i}].name is empty")
            attrs = [item['name'] for item in attrs]
            await register_schema(did=payload_['did'], name=payload_['name'], ver=payload_['ver'], attrs=attrs)
        elif action_ == 'load-schema':
            name = payload_.get('name')
            if not name:
                raise HTTPException(status_code=400, detail=f"Schema-ID is empty")
            success, schema = await load_schema(schema_id=name)
            if success:
                return dict(**schema.body)
            else:
                raise HTTPException(status_code=400, detail=f"Not found Schema with same ID")
        elif action_ == 'store-loaded-schema':
            name = payload_.get('name')
            if not name:
                raise HTTPException(status_code=400, detail=f"Schema-ID is empty")
            await store_dkms_schema(schema_id=name)
        elif action_ == 'reset':
            confirm = payload_.get('confirm')
            if confirm and confirm.lower() == 'reset':
                await reset()
            else:
                raise HTTPException(status_code=400, detail="Confirmation declined")
        elif action_ == 'register-cred-def':
            did = payload_['did']
            if ':' in did:
                did = did.split(':')[-1]
            schema_id = payload_['schema_id']
            tag = payload_.get('tag', None)
            if not tag:
                raise HTTPException(status_code=400, detail="TAG is Empty!")
            await register_cred_def(schema_id, tag, did)
        elif action_ == 'issue-cred':
            their_did = payload_.pop('to')
            if ':' in their_did:
                their_did = their_did.split(':')[-1]
            cred_def_id = payload_.pop('cred_def_id')
            values = dict(**payload_)
            for name, value in values.items():
                if not value:
                    raise HTTPException(status_code=400, detail=f"{name} attrib is Empty!")
            await issue_cred(their_did, values, cred_def_id)
        elif action_ == 'verify':
            their_did = payload_.pop('their_did')
            if ':' in their_did:
                their_did = their_did.split(':')[-1]
            proof_request = payload_.pop('proof_request')
            success, msg = await verify(their_did, proof_request=proof_request)
            return {
                'success': success,
                'msg': msg
            }
    except RuntimeError as e:
        msg = ''
        for arg in e.args:
            if type(arg) is str:
                msg = arg
                break
        raise HTTPException(status_code=400, detail=msg)
    else:
        return {'success': True}


@app.websocket("/")
async def events(websocket: WebSocket):
    await websocket.accept()
    listener = await sirius_sdk.subscribe()
    async for event in listener:
        if isinstance(event.message, sirius_sdk.aries_rfc.Message):
            content = event.message.content
            print(f'Received text message: {content}')
            their_vk = event.sender_verkey
            my_vk = event.recipient_verkey
            conn_ = await get_my_connections(their_verkey=their_vk, my_verkey=my_vk)
            if conn_:
                p2p = conn_[0]
                await websocket.send_json({
                    'topic': 'messaging.rcv',
                    'payload': {
                        'msg': content,
                        'their_did': p2p.their.did
                    }
                })
            else:
                print(f'Not found P2P for verkey: {their_vk}')


@app.get("/health_check")
async def health_check():
    return {"utc": datetime.utcnow().isoformat()}


def thread_routine():
    loop = asyncio.new_event_loop()
    while True:
        logging.warning('Run loop')
        try:
            loop.run_until_complete(foreground())
        except Exception as e:
            logging.exception('Exception')
        logging.warning('Sleep before re-run loop')
        sleep(3)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--production', choices=['on', 'yes'], required=False)
    args = parser.parse_args()
    is_production = args.production is not None
    args = ()
    kwargs = {}
    f = asyncio.ensure_future(foreground())
    th = threading.Thread(target=thread_routine)
    th.daemon = True
    th.start()
    if is_production:
        logging.warning('\n')
        logging.warning('\t*************************************')
        logging.warning('\tApplication will be run in PRODUCTION mode')
        logging.warning('\t*************************************')
        args = ['app.main:app']
        kwargs['proxy_headers'] = True
        kwargs.update({'reload': True})
        uvicorn.run(*args, host="0.0.0.0", port=80, workers=int(os.getenv('WORKERS')), **kwargs)
    else:
        logging.warning('\n')
        logging.warning('\t*************************************')
        logging.warning('\tApplication will be run in DEBUG mode')
        logging.warning('\t*************************************')
        uvicorn.run(app, host="0.0.0.0", port=80, **kwargs)
