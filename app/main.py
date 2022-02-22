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
from didcomm.const import MSG_TYP_GOSSYP, MSG_TYP_TRACE_RESP
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

GOSSYP_DEMO = {
    "nodes": [
        {"id": "priemosdatchik", "human": True, "name": "Приемосдатчик", "loaded": False, "auras": ["Подача и уборка вагона"]},
        {"id": "shipper", "human": True, "name": "Грузоотправитель", "loaded": False, "auras": ["Оформление груза"]},
        {"id": "tvk", "human": True, "name": "ТВК", "loaded": False, "auras": ["Оплата накладной"]},
        {"id": "asu_dkr", "human": False, "name": "АСУ ДКР", "loaded": False, "auras": ["Оформление груза", "Оплата накладной"]},
        {"id": "asu_st", "human": False, "name": "АСУ СТ", "loaded": False, "auras": ["Подача и уборка вагона", "Оформление груза"]},
        {"id": "asoup", "human": False, "name": "АСОУП", "loaded": False, "auras": ["Оплата накладной"]},
        {"id": "ekiodv", "human": False, "name": "ЕКИОДВ", "loaded": True, "auras": ["Оплата накладной"]},
    ],
    "links": [
        {"id": "1", "from": "priemosdatchik", "to": "asu_st", "label": "Заполнение ведомости", "request": True},
        {"id": "2", "from": "asu_st", "to": "priemosdatchik", "label": "Готовая форма ГУ-46", "request": False},
        {"id": "3", "from": "shipper", "to": "asu_dkr", "label": "Оформление накладной", "request": True},
        {"id": "4", "from": "asu_dkr", "to": "shipper", "label": "Накладная создана", "request": False},
        {"id": "5", "from": "asu_dkr", "to": "asu_st", "label": "Проверка ГУ-46", "request": True},
        {"id": "6", "from": "asu_st", "to": "asu_dkr", "label": "Ответ", "request": False},
        {"id": "7", "from": "tvk", "to": "asu_dkr", "label": "Платеж", "request": True},
        {"id": "8", "from": "asu_dkr", "to": "tvk", "label": "Оплачено", "request": False},
        {"id": "9", "from": "asu_dkr", "to": "asoup", "label": "410", "request": True},
        {"id": "10", "from": "asoup", "to": "asu_dkr", "label": "Результат проверки", "request": False},
        {"id": "11", "from": "asoup", "to": "ekiodv", "label": "410", "request": True},
        {"id": "12", "from": "ekiodv", "to": "asoup", "label": "Результат проверки", "request": False},
    ]
}


AURAS_MY_CONNECTIONS = settings.TITLE
NODE_ID_ME = 'me'


def build_connection_graph(connections: list) -> dict:
    nodes = [
        {
            "id": NODE_ID_ME,
            "human": False,
            "name": "MySelf",
            "loaded": True,
            "locked": "pinned",
            "auras": [AURAS_MY_CONNECTIONS],
            "style": {"fillColor": "orange"}
        }
    ]
    links = []
    """
    for conn in connections:
        id = conn['their']['did']
        nodes.append({
            "id": id,
            "human": False,
            "name": conn['their']['label'],
            "loaded": True,
            "auras": [AURAS_MY_CONNECTIONS]
        })
        links.append({
            "id": str(len(links)),
            "from": "me",
            "to": id,
            "label": "P2P",
        })
    """
    return {
        "nodes": nodes,
        "links": links
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
        }),
        'conn_graph': build_connection_graph(connections),
        'gossyp_demo': GOSSYP_DEMO,
        'auras_my_connections': AURAS_MY_CONNECTIONS
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
        elif action_ == 'gossyp':
            members = []
            for did in payload_['members']:
                if ':' in did:
                    did = did.split(':')[-1]
                members.append(did)
            message = payload_['message']
            try:
                await gossyp(members, message)
            except Exception as e:
                raise
        elif action_ == 'route':
            their_did = payload_['their_did']
            graph = await fire_route(their_did)
            if graph:
                graph = await refresh_graph(graph)
                return {'graph': graph, 'pending': False}
            else:
                return {'graph': None, 'pending': True}
    except RuntimeError as e:
        msg = ''
        for arg in e.args:
            if type(arg) is str:
                msg = arg
                break
        raise HTTPException(status_code=400, detail=msg)
    else:
        return {'success': True}


async def refresh_graph(graph: dict) -> dict:
    my_dids = []
    my_identities = await get_my_identities()
    for item in my_identities:
        tags = item['tags']
        did = tags["did"]
        my_dids.append(did)
    nodes = graph.get('nodes', [])
    updated_nodes = []
    for node in nodes:
        did = node['id']
        if did not in my_dids:
            updated_nodes.append(node)
    links = graph.get('links', [])
    updated_links = []
    for link in links:
        from_ = link['from']
        to_ = link['to']
        if from_ in my_dids:
            link['from'] = NODE_ID_ME
        if to_ in my_dids:
            link['to'] = NODE_ID_ME
        updated_links.append(link)
    graph['nodes'] = updated_nodes
    graph['links'] = updated_links
    return graph


@app.websocket("/")
async def events(websocket: WebSocket):
    cached_gossyp_ids = []
    cached_gossyp_graph_hashes = {}
    await websocket.accept()
    listener = await sirius_sdk.subscribe()
    async for event in listener:
        if isinstance(event.message, sirius_sdk.aries_rfc.Message):
            content = event.message.content
            print(f'Received text message: {content}')
            print(event.message.type)
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
        elif event.message.type == MSG_TYP_TRACE_RESP:
            print('Received Trace response')
            route = event.message.get('route', [])
            graph = event.message.get('graph', {})
            if route and graph:
                did = route[0]
                my_conn = await get_my_connections()
                my_dids = [p2p.me.did for p2p in my_conn]
                participants = {p2p.their.did: p2p for p2p in my_conn}
                graph = await update_graph(graph, participants)
                graph = await refresh_graph(graph)
                if did in my_dids:
                    await websocket.send_json({
                        'topic': 'gossyp.graph',
                        'payload': {
                            'graph': graph,
                        }
                    })
        elif event.message.type == MSG_TYP_GOSSYP:
            print('Received Gossyp')
            if event.message.id in cached_gossyp_ids:
                graph = event.message.get('graph', {})
                graph_hash = calc_json_hash(graph)
                if cached_gossyp_graph_hashes[event.message.id] != graph_hash:
                    cached_gossyp_graph_hashes[event.message.id] = graph_hash
                    graph = event.message.get('graph', None)
                    if graph:
                        graph = await refresh_graph(graph)
                        await websocket.send_json({
                            'topic': 'gossyp.graph',
                            'payload': {
                                'graph': graph,
                            }
                        })
                        print('Raised graph update')
                else:
                    print('Ignore cause of message with same ID already processed...')
            else:
                print(json.dumps(event.message, indent=2, sort_keys=True))
                members = event.message.get('members', [])
                content = event.message.get('content', None)
                graph = event.message.get('graph', None)

                graph_hash = calc_json_hash(graph)
                cached_gossyp_graph_hashes[event.message.id] = graph_hash

                from_p2p = event.pairwise

                if graph:
                    graph = await refresh_graph(graph)
                await websocket.send_json({
                    'topic': 'messaging.gossyp',
                    'payload': {
                        'msg': content,
                        'members': members,
                        'graph': graph,
                        'from': from_p2p.their.did if from_p2p else None
                    }
                })
                cached_gossyp_ids.append(event.message.id)


@app.get("/health_check")
async def health_check(request: Request):
    return {"utc": datetime.utcnow().isoformat(), "headers": request.headers}


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
