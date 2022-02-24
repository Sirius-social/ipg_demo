import json
import logging
import hashlib
import uuid

from typing import Optional, List, Union

import sirius_sdk
from sirius_sdk.agent.wallet.abstract import NYMRole as ActorRole
from sirius_sdk.agent.wallet.abstract.non_secrets import RetrieveRecordOptions
from sirius_sdk.agent.wallet.abstract.anoncreds import AnonCredSchema
from sirius_sdk.agent.ledger import Schema, SchemaFilters, CredentialDefinition
from sirius_sdk.errors.indy_exceptions import AnoncredsMasterSecretDuplicateNameError, WalletItemAlreadyExists
from sirius_sdk.agent.aries_rfc.feature_0036_issue_credential.messages import ProposedAttrib

import settings
from machine_readable_govs.utils import extract_my_roles
from didcomm.const import *
from settings import DKMS_NETWORK, STEWARD_DID, SDK_STEWARD, MASTER_SECRET_ID, TITLE


IDENTITIES_TYPE = 'demo_identities'
CONNECTIONS_TYPE = 'demo_connections'
SCHEMAS_TYPE = 'demo_schemas'
CREDS_TYPE = 'demo_credentials'


class ConsoleLogger:

    async def __call__(self, *args, **kwargs):
        data = kwargs
        print('---------------------LOG------------------------')
        print(json.dumps(data, indent=2, sort_keys=True))


async def steward_register_nym(did: str, verkey: str, role: ActorRole=ActorRole.TRUST_ANCHOR, alias: str = ''):
    print(f'registering did: {did}')
    async with sirius_sdk.context(**SDK_STEWARD):
        dkms = await sirius_sdk.ledger(DKMS_NETWORK)
        success, op = await dkms.write_nym(STEWARD_DID, did, verkey, role=role, alias=alias)
        if not success:
            raise RuntimeError('')
    print('did wass successfully registered')


async def get_my_endpoint():
    endpoints = await sirius_sdk.endpoints()
    my_endpoint = [e for e in endpoints if e.routing_keys == []][0]
    return my_endpoint


async def get_my_identities(**search):
    opts = RetrieveRecordOptions()
    opts.check_all()
    search_with_tags = dict(**search)
    my_identities, count = await sirius_sdk.NonSecrets.wallet_search(
        IDENTITIES_TYPE, search_with_tags, opts, 100
    )
    return my_identities or []


async def get_my_connections(**search):
    opts = RetrieveRecordOptions()
    opts.check_all()
    search_with_tags = dict(**search)
    my_connections_raw, count = await sirius_sdk.NonSecrets.wallet_search(
        CONNECTIONS_TYPE, search_with_tags, opts, 100
    )
    my_connections_raw = my_connections_raw or []
    my_connections = []
    for raw in my_connections_raw:
        metadata = json.loads(raw['value'])
        p2p = sirius_sdk.Pairwise(
            me=sirius_sdk.Pairwise.Me(
                did=metadata.get('me', {}).get('did', None),
                verkey=metadata.get('me', {}).get('verkey', None),
                did_doc=metadata.get('me', {}).get('did_doc', None)
            ),
            their=sirius_sdk.Pairwise.Their(
                did=metadata.get('their', {}).get('did', None),
                verkey=metadata.get('their', {}).get('verkey', None),
                label=metadata.get('their', {}).get('label', None),
                endpoint=metadata.get('their', {}).get('endpoint', {}).get('address', None),
                routing_keys=metadata.get('their', {}).get('endpoint', {}).get('routing_keys', None),
                did_doc=metadata.get('their', {}).get('did_doc', None)
            ),
            metadata=metadata
        )
        my_connections.append(p2p)
    return my_connections or []


async def get_my_schemas(**search):
    opts = RetrieveRecordOptions()
    opts.check_all()
    search_with_tags = dict(**search)
    my_schemas_raw, count = await sirius_sdk.NonSecrets.wallet_search(
        SCHEMAS_TYPE, search_with_tags, opts, 100
    )
    my_schemas_raw = my_schemas_raw or []
    my_schemas = []
    for raw in my_schemas_raw:
        schema = Schema(**json.loads(raw['value']))
        schema.cred_defs = []
        tags = raw.get('tags', {})
        for n, val in tags.items():
            if n.startswith('cred_def_'):
                schema.cred_defs.append(val)
        my_schemas.append(schema)
    return my_schemas or []


async def get_my_credentials():
    opts = RetrieveRecordOptions()
    opts.check_all()
    search_with_tags = {}
    my_creds_raw, count = await sirius_sdk.NonSecrets.wallet_search(
        CREDS_TYPE, search_with_tags, opts, 100
    )
    credentials = []
    if my_creds_raw:
        for raw in my_creds_raw:
            s = raw['value']
            cred = json.loads(s)
            cred['id'] = raw['id']
            if 'issuer_did' not in cred:
                cred['issuer_did'] = None
            credentials.append(cred)
    return credentials


async def reset():
    # delete schemas
    my_schemas = await get_my_schemas()
    for item in my_schemas:
        await sirius_sdk.NonSecrets.delete_wallet_record(SCHEMAS_TYPE, item.id)
    # delete credentials
    my_creds = await get_my_credentials()
    for item in my_creds:
        await sirius_sdk.NonSecrets.delete_wallet_record(CREDS_TYPE, item['id'])
    # delete identities
    my_identities = await get_my_identities()
    for item in my_identities:
        did = item['tags']['did']
        await sirius_sdk.NonSecrets.delete_wallet_record(IDENTITIES_TYPE, did)
        pass
    # delete connections
    my_connections = await get_my_connections()
    for item in my_connections:
        conn_id = build_connection_id(item.their.did, item.me.did)
        await sirius_sdk.NonSecrets.delete_wallet_record(CONNECTIONS_TYPE, conn_id)
        pass
    pass


async def create_identity(label: str) -> (str, str):
    """
    Create new Identity is SSI world

    :param label: human-readable presentation
    :return: DID, invitation-string
    """
    did, verkey = await sirius_sdk.DID.create_and_store_my_did()
    await steward_register_nym(did, verkey, alias=label)
    my_endpoint = await get_my_endpoint()
    inv = sirius_sdk.aries_rfc.Invitation(
        label=label,
        recipient_keys=[verkey],
        endpoint=my_endpoint.address
    )
    inv_s = inv.invitation_url
    js = {'did': did, 'inv': inv_s, 'label': label, 'verkey': verkey}
    await sirius_sdk.NonSecrets.add_wallet_record(
        type_=IDENTITIES_TYPE, id_=did, value=json.dumps(js),
        tags=js
    )
    return did, inv_s


async def register_connection(p2p: sirius_sdk.Pairwise):
    await sirius_sdk.PairwiseList.ensure_exists(p2p)
    tags = {
        'my_did': p2p.me.did, 'my_verkey': p2p.me.verkey,
        'their_did': p2p.their.did, 'their_verkey': p2p.their.verkey
    }
    try:
        conn_id = build_connection_id(p2p.their.did, p2p.me.did)
        await sirius_sdk.NonSecrets.add_wallet_record(
            type_=CONNECTIONS_TYPE, id_=conn_id, value=json.dumps(p2p.metadata),
            tags=tags
        )
    except WalletItemAlreadyExists:
        pass


async def store_schema_in_wallet(did: str, name: str, ver: str, schema: Schema):
    try:
        opts = RetrieveRecordOptions()
        opts.check_all()
        rec = await sirius_sdk.NonSecrets.get_wallet_record(SCHEMAS_TYPE, schema.id, opts)
    except:
        exists = False
    else:
        exists = True
    if not exists:
        await sirius_sdk.NonSecrets.add_wallet_record(
            type_=SCHEMAS_TYPE, id_=schema.id, value=json.dumps(schema.body),
            tags={'did': did, 'name': name, 'ver': ver}
        )


def build_schema_tag_name_for_cred_def(cred_def_id: str):
    return f'cred_def_{cred_def_id}'


def build_connection_id(their_did: str, my_did: str) -> str:
    return f'{their_did}:{my_did}'


async def register_cred_def_for_schema(cred_def_id: str, schema_id: str):
    tag_name = build_schema_tag_name_for_cred_def(cred_def_id)
    await sirius_sdk.NonSecrets.add_wallet_record_tags(
        SCHEMAS_TYPE,
        schema_id,
        # extended tags
        tags={tag_name: cred_def_id}
    )


async def store_dkms_schema(schema_id: str):
    success, schema = await load_schema(schema_id)
    if success:
        did = schema_id.split(':')[0]
        await store_schema_in_wallet(did, schema.name, schema.version, schema)
        print('')
    else:
        raise RuntimeError(f'Schema with ID: {schema_id} does not exists!')


async def register_schema(did: str, name: str, ver: str, attrs: list):
    if ':' in did:
        did = did.split(':')[-1]
    print('registering schema')
    schema_id_, schema = await sirius_sdk.AnonCreds.issuer_create_schema(
        did, name, ver, attrs
    )
    dkms = await sirius_sdk.ledger(DKMS_NETWORK)
    success, stored_schema = await dkms.register_schema(schema, did)
    print('schema stored to DKMS')
    await store_schema_in_wallet(did, name, ver, stored_schema)
    print('schema registered')


async def register_cred(cred_id: str, preview: List[ProposedAttrib] = None, comment: str = None, issuer_did: str = None):
    try:
        await sirius_sdk.NonSecrets.delete_wallet_record(CREDS_TYPE, cred_id)
    except:
        pass
    if preview:
        values = [item.to_json() for item in preview]
        value_as_str = json.dumps({
            'comment': comment,
            'issuer_did': issuer_did,
            'preview': values
        })
        await sirius_sdk.NonSecrets.add_wallet_record(type_=CREDS_TYPE, id_=cred_id, value=value_as_str)


async def load_schema(schema_id: str) -> (bool, Optional[Schema]):
    print(f'loading schema-id: {schema_id}')
    async with sirius_sdk.context(**SDK_STEWARD):
        dkms = await sirius_sdk.ledger(DKMS_NETWORK)
        try:
            schema = await dkms.load_schema(schema_id, STEWARD_DID)
            success = True
        except:
            success, schema = False, None
    if success:
        print('schema was successfully loaded')
        print(json.dumps(schema.body, indent=2, sort_keys=True))
    else:
        print('schema not loaded, Error!')
    return success, schema


async def register_cred_def(schema_id: str, tag: str, did: str):
    schemas = await get_my_schemas()
    schema = None
    for s in schemas:
        if s.id == schema_id:
            schema = s
            break
    if not schema:
        raise RuntimeError(f'Schema with ID: {schema_id} not found!')
    print('Registering Cred-Def...')
    try:
        cred_def = CredentialDefinition(tag, schema)
        dkms = await sirius_sdk.ledger(DKMS_NETWORK)

        success, ledger_cred_def = await dkms.register_cred_def(cred_def, did)
        if success:
            await register_cred_def_for_schema(ledger_cred_def.id, schema_id)
            print('Successfully registered Cred-Def')
        else:
            raise RuntimeError('Error while registering Cred-Def')
    except Exception as e:
        print(str(e))
        raise RuntimeError('Error while registering Cred-Def')


async def establish_connection_as_inviter(
        me: sirius_sdk.Pairwise.Me,
        my_endpoint: sirius_sdk.Endpoint,
        connection_key: str,
        request: sirius_sdk.aries_rfc.ConnRequest
):
    log = ConsoleLogger()
    sm = sirius_sdk.aries_rfc.Inviter(
        me=me,
        connection_key=connection_key,
        my_endpoint=my_endpoint,
        logger=log
    )
    success, p2p = await sm.create_connection(request)
    if success:
        await log('P2P was established successfully!')
        await register_connection(p2p)
    else:
        msg = sm.problem_report.explain if sm.problem_report else ''
        await log(f'Error while P2P establishing: "{msg}"')


async def establish_connection_as_invitee(me: sirius_sdk.Pairwise.Me, my_label: str, invitation: sirius_sdk.aries_rfc.Invitation):
    my_endpoint = await get_my_endpoint()
    log = ConsoleLogger()
    sm = sirius_sdk.aries_rfc.Invitee(me, my_endpoint, logger=log)
    ok, p2p = await sm.create_connection(invitation=invitation, my_label=my_label)
    if ok:
        await register_connection(p2p)


async def issue_cred(their_did: str, values: dict, cred_def_id: str, comment: str = 'Empty comment'):
    holder = await sirius_sdk.PairwiseList.load_for_did(their_did)
    if not holder:
        raise RuntimeError(f'Not found P2P for Their DID: {their_did}')
    tag_name = build_schema_tag_name_for_cred_def(cred_def_id)
    schemas = await get_my_schemas(**{tag_name: cred_def_id})
    if not schemas:
        raise RuntimeError(f'Nor found schema for Cred-Def: {cred_def_id}')
    schema = schemas[0]
    values = {name: value for name, value in values.items() if name in schema.attributes}
    if set(values.keys()) != set(schema.attributes):
        raise RuntimeError('Values set not equal to schema attribute set')
    preview = []
    for name, value in values.items():
        preview.append(
            ProposedAttrib(name, value)
        )

    my_did = holder.me.did
    dkms = await sirius_sdk.ledger(DKMS_NETWORK)
    schema = await dkms.load_schema(schema.id, my_did)
    cred_def = await dkms.load_cred_def(cred_def_id, my_did)
    ttl = 15
    cred_id = f'{cred_def_id}:{my_did}->{their_did}'
    cred_id = hashlib.sha256(cred_id.encode()).hexdigest()

    machine = sirius_sdk.aries_rfc.Issuer(holder=holder, logger=ConsoleLogger(), time_to_live=ttl)
    success = await machine.issue(
        values=values,
        schema=schema,
        cred_def=cred_def,
        comment=comment,
        preview=preview,
        cred_id=cred_id
    )
    return success


async def verify(their_did: str, proof_request: dict) -> (bool, Optional[dict]):
    prover = await sirius_sdk.PairwiseList.load_for_did(their_did)
    if not prover:
        raise RuntimeError(f'Not found P2P for Their DID: {their_did}')
    dkms = await sirius_sdk.ledger(DKMS_NETWORK)

    ttl = 30
    machine = sirius_sdk.aries_rfc.Verifier(prover=prover, ledger=dkms, time_to_live=ttl)
    try:
        success = await machine.verify(proof_request, proto_version='1.0')
        if success:
            return True, machine.revealed_attrs
        else:
            return False, machine.problem_report
    except Exception as e:
        logging.exception('Verify Exception!!!')
        raise


async def gossyp(members: list, msg: str = None):
    msg = sirius_sdk.messaging.Message({
        '@type': MSG_TYP_GOSSYP,
        'members': members,
        'content': msg
    })
    for member in members:
        p2p = await sirius_sdk.PairwiseList.load_for_did(member)
        if p2p:
            await sirius_sdk.send_to(msg, p2p)
        else:
            logging.error(f'Not found P2P for DID: {member}')


def calc_json_hash(value: Union[list, dict]) -> str:
    js = json.dumps(value, sort_keys=True)
    hashed = hashlib.sha256(js.encode()).hexdigest()
    return hashed


async def update_graph(graph: dict, participants: dict) -> dict:
    nodes = graph.get('nodes', [])
    links = graph.get('links', [])
    my_aura = settings.TITLE
    nodes_as_dict = {item['id']: item for item in nodes}
    links_as_dict = {item['id']: item for item in links}
    for did, p2p in participants.items():
        if did in nodes_as_dict:
            auras = nodes_as_dict[did].get('auras', [])
            if my_aura not in auras:
                auras.append(my_aura)
                nodes_as_dict[did]['auras'] = auras
        else:
            nodes_as_dict[did] = {
                "id": p2p.their.did,
                "loaded": True,
                "name": p2p.their.label,
                "auras": [my_aura]
            }
        my_did = p2p.me.did
        if my_did in nodes_as_dict:
            auras = nodes_as_dict[my_did].get('auras', [])
            if my_aura not in auras:
                auras.append(my_aura)
                nodes_as_dict[did]['auras'] = auras
        else:
            nodes_as_dict[my_did] = {
                "id": my_did,
                "loaded": True,
                "name": TITLE,
                "auras": [my_aura]
            }
        link_id = p2p.me.did + '>' + p2p.their.did
        if link_id not in links_as_dict:
            links_as_dict[link_id] = {
                "id": link_id,
                "from": p2p.me.did, "to": p2p.their.did, "label": "P2P"
            }
        '''
        nodes: [
            { id: their_did, loaded: true, name: conn.their.label, auras: "{{ auras_my_connections }}" },
        ], links: [
            { id: their_did, from: 'me', to: their_did, label: "P2P" }
        ]
        '''
    nodes = [value for key, value in nodes_as_dict.items()]
    links = [value for key, value in links_as_dict.items()]
    graph['nodes'] = nodes
    graph['links'] = links
    return graph


async def build_mrg_graph(my_roles: list, p2p: sirius_sdk.Pairwise) -> dict:
    nodes = [
        {
            "id": p2p.me.did,
            "loaded": True,
            "name": TITLE,
            "auras": my_roles
        }
    ]
    link_id = p2p.me.did + '>' + p2p.their.did
    links = [
        {
            "id": link_id,
            "from": p2p.me.did, "to": p2p.their.did, "label": "P2P"
        }
    ]
    return {
        'nodes': nodes,
        'links': links
    }


async def fire_route(their_did: str, route: list = None, msg_id: str = None) -> Optional[dict]:
    p2p = await sirius_sdk.PairwiseList.load_for_did(their_did)
    if p2p:
        participants = {their_did: p2p}
        graph = await update_graph(graph={}, participants=participants)
        print(f'Found P2P: {their_did}')
        return graph
    else:
        route = route or []
        my_connections = await get_my_connections()
        for p2p in my_connections:
            if their_did not in (p2p.their.did, p2p.me.did):
                cur_route = [item for item in route]
                cur_route.append(p2p.me.did)
                msg = sirius_sdk.messaging.Message({
                    '@id': msg_id or uuid.uuid4().hex,
                    '@type': MSG_TYP_TRACE_REQ,
                    'route': cur_route,
                    'did': their_did
                })
                await sirius_sdk.send_to(msg, p2p)
        return None


async def fire_compliance(doc, req_id):
    my_connections = await get_my_connections()
    msg = sirius_sdk.messaging.Message({
        '@id': req_id,
        '@type': MSG_TYP_MRG_REQUEST,
        'doc': doc,
    })
    for p2p in my_connections:
        route = [p2p.me.did]
        msg['route'] = route
        await sirius_sdk.send_to(msg, p2p)


async def foreground():
    cached_gossyp_ids = []
    cached_trace_ids = []
    try:
        await sirius_sdk.AnonCreds.prover_create_master_secret(MASTER_SECRET_ID)
    except AnoncredsMasterSecretDuplicateNameError as e:
        pass
    my_endpoint = await get_my_endpoint()
    dkms = await sirius_sdk.ledger(DKMS_NETWORK)
    listener = await sirius_sdk.subscribe()  # group_id='IPG_DEMO_FOREGROUND'
    async for event in listener:
        if isinstance(event.message, sirius_sdk.aries_rfc.ConnRequest):
            # check if it is self invitation
            found_identities = await get_my_identities(verkey=event.sender_verkey)
            if found_identities:
                logging.error('Mistake: you sent invitation to yourself!')
            else:
                found_identities = await get_my_identities(verkey=event.recipient_verkey)
                if found_identities:
                    my_identity = found_identities[0]['tags']
                    me = sirius_sdk.Pairwise.Me(
                        did=my_identity['did'],
                        verkey=my_identity['verkey']
                    )
                    await establish_connection_as_inviter(me, my_endpoint, event.recipient_verkey, event.message)
                else:
                    logging.warning(f'Aries-RFC[0160]: Not found identity for recipient_verkey: {event.recipient_verkey}')
        elif isinstance(event.message, sirius_sdk.aries_rfc.OfferCredentialMessage):
            print('====== Received Credential Offer, Apply IT!!! ============')
            ttl = 15
            offer = event.message
            if event.pairwise:
                machine = sirius_sdk.aries_rfc.Holder(issuer=event.pairwise, time_to_live=ttl, logger=ConsoleLogger())
                success, cred_id = await machine.accept(
                    offer,
                    MASTER_SECRET_ID,
                    comment=f'Hello, Iam {TITLE}',
                    ledger=dkms
                )
                if success:
                    print(f'Register Cred with ID: {cred_id}')
                    issuer_did = event.pairwise.their.did
                    await register_cred(cred_id, preview=offer.preview, comment=offer.comment, issuer_did=issuer_did)
            else:
                print('Offer pairwise is Empty')
        elif isinstance(event.message, sirius_sdk.aries_rfc.RequestPresentationMessage):
            print('====== Received RequestPresentationMessage, try verify proof !!! ============')
            ttl = 30
            request = event.message
            if event.pairwise:
                machine = sirius_sdk.aries_rfc.Prover(
                    verifier=event.pairwise, ledger=dkms, time_to_live=ttl, logger=ConsoleLogger()
                )
                success = await machine.prove(request, MASTER_SECRET_ID)
                print(f'Verify proof status: {success}')
            else:
                print('ProofRequest pairwise is Empty')
        elif event.message.type == MSG_TYP_TRACE_REQ:
            print(f'========== Received Route Request============')
            print(json.dumps(event.message, indent=2, sort_keys=True))
            route = event.message.get('route', [])
            route_as_set = list(set(route))
            if event.message.id in cached_trace_ids:
                print('Ignore trace request')
            elif len(route) != len(route_as_set):
                print('Ignore trace request cause of Loop')
            else:
                cached_trace_ids.append(event.message.id)
                did = event.message.get('did', None)
                route = event.message.get('route', [])
                if did and route:
                    p2p = await sirius_sdk.PairwiseList.load_for_did(did)
                    if p2p:
                        print('Found P2P, make route response')
                        graph = await fire_route(did, route, msg_id=event.message.id)
                        prev_did = route[-1]
                        prev_p2p = await sirius_sdk.PairwiseList.load_for_did(prev_did)
                        if prev_p2p:
                            resp = sirius_sdk.messaging.Message({
                                '@id': event.message.id,
                                '@type': MSG_TYP_TRACE_RESP,
                                'route': route,
                                'did': did,
                                'graph': graph
                            })
                            await sirius_sdk.send_to(resp, prev_p2p)
                        else:
                            print(f'Not found prev_p2p for DID: {prev_did}')
                    else:
                        await fire_route(did, route, msg_id=event.message.id)

        elif event.message.type == MSG_TYP_TRACE_RESP:
            print(f'========== Received Route Response============')
            print(json.dumps(event.message, indent=2, sort_keys=True))
            route = event.message.get('route', [])
            prev_route = []
            for did in route:
                p2p = await sirius_sdk.PairwiseList.load_for_did(did)
                if p2p:
                    print(f'found p2p for did: {did}')
                    if prev_route:
                        prev_did = prev_route[-1]
                        print(f'prev route did: {prev_did}')
                        prev_p2p = await sirius_sdk.PairwiseList.load_for_did(prev_did)
                        if prev_p2p:
                            await sirius_sdk.send_to(event.message, prev_p2p)
                        else:
                            print(f'not found p2p for did: {prev_did}')
                else:
                    prev_route.append(did)
        elif event.message.type == MSG_TYP_GOSSYP:
            if event.message.id not in cached_gossyp_ids:
                print(f'========== Re-Raise Gossyp Message with ID: {event.message.id}')
                cached_gossyp_ids.append(event.message.id)
                members = event.message.get('members', [])
                reraise_members = {}
                for did in members:
                    p2p = await sirius_sdk.PairwiseList.load_for_did(did)
                    if p2p:
                        reraise_members[did] = p2p
                print('Re-Raise members: ' + str(list(reraise_members.keys())))
                old_graph_hash = None
                new_graph_hash = None
                if reraise_members:
                    graph = event.message.get('graph', {})
                    old_graph_hash = calc_json_hash(graph)
                    graph = await update_graph(graph, reraise_members)
                    new_graph_hash = calc_json_hash(graph)
                    event.message['graph'] = graph
                for did, p2p in reraise_members.items():
                    if did in (event.pairwise.their.did, event.pairwise.me.did):
                        pass
                    else:
                        await sirius_sdk.send_to(event.message, p2p)
        elif event.message.type == MSG_TYP_MRG_REQUEST:
            print(f'========== Received MRG request with ID: {event.message.id}')
            doc = event.message.get('doc')
            if doc:
                roles = await extract_my_roles(doc)
                graph = await build_mrg_graph(roles, event.pairwise)
                init_route = event.message.get('route', [])
                msg = sirius_sdk.messaging.Message({
                    '@id': event.message.id,
                    '@type': MSG_TYP_MRG_RESP,
                    'graph': graph,
                    'route': init_route
                })
                await sirius_sdk.send_to(msg, event.pairwise)
                my_connections = await get_my_connections()

                req = sirius_sdk.messaging.Message({
                    '@id': event.message.id,
                    '@type': MSG_TYP_MRG_REQUEST,
                    'doc': doc
                })
                print('re-send to participants')
                for p2p in my_connections:
                    if p2p.their.did != event.pairwise.their.did:
                        route = [item for item in init_route]
                        route.append(p2p.me.did)
                        req['route'] = route
                        await sirius_sdk.send_to(req, p2p)
            else:
                print('---- DOC is empty ---')
        elif event.message.type == MSG_TYP_MRG_RESP:
            print(f'========== Received MRG response with ID: {event.message.id}')
            print(json.dumps(event.message, indent=2, sort_keys=True))
            route = event.message.get('route', [])
            prev_route = []
            my_conns = await get_my_connections()
            for did in route:
                search = [p2p for p2p in my_conns if p2p.me.did == did]
                if search:
                    p2p = search[0]
                else:
                    p2p = None
                if p2p:
                    print(f'found p2p for did: {did}')
                    if prev_route:
                        prev_did = prev_route[-1]
                        print(f'prev route did: {prev_did}')
                        prev_p2p = await sirius_sdk.PairwiseList.load_for_did(prev_did)
                        if prev_p2p:
                            await sirius_sdk.send_to(event.message, prev_p2p)
                        else:
                            print(f'not found p2p for did: {prev_did}')
                else:
                    prev_route.append(did)