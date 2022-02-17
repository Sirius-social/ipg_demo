import json
import logging
from typing import Optional

import sirius_sdk
from sirius_sdk.agent.wallet.abstract import NYMRole as ActorRole
from sirius_sdk.agent.wallet.abstract.non_secrets import RetrieveRecordOptions
from sirius_sdk.agent.wallet.abstract.anoncreds import AnonCredSchema
from sirius_sdk.agent.ledger import Schema, SchemaFilters

from settings import DKMS_NETWORK, STEWARD_DID, SDK_STEWARD


IDENTITIES_TYPE = 'demo_identities'
CONNECTIONS_TYPE = 'demo_connections'
SCHEMAS_TYPE = 'demo_schemas'


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
        my_schemas.append(schema)
    return my_schemas or []


async def reset():
    # delete schemas
    my_schemas = await get_my_schemas()
    for item in my_schemas:
        await sirius_sdk.NonSecrets.delete_wallet_record(SCHEMAS_TYPE, item.id)
    # delete identities
    my_identities = await get_my_identities()
    for item in my_identities:
        did = item['tags']['did']
        await sirius_sdk.NonSecrets.delete_wallet_record(IDENTITIES_TYPE, did)
        pass
    # delete connections
    my_connections = await get_my_connections()
    for item in my_connections:
        await sirius_sdk.NonSecrets.delete_wallet_record(CONNECTIONS_TYPE, item.their.did)
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
    await sirius_sdk.NonSecrets.add_wallet_record(
        type_=CONNECTIONS_TYPE, id_=tags['their_did'], value=json.dumps(p2p.metadata),
        tags=tags
    )


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


async def foreground():
    my_endpoint = await get_my_endpoint()
    listener = await sirius_sdk.subscribe(group_id='IPG_DEMO_FOREGROUND')
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
