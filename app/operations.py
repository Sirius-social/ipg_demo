import json
import logging
import hashlib
from typing import Optional, List

import sirius_sdk
from sirius_sdk.agent.wallet.abstract import NYMRole as ActorRole
from sirius_sdk.agent.wallet.abstract.non_secrets import RetrieveRecordOptions
from sirius_sdk.agent.wallet.abstract.anoncreds import AnonCredSchema
from sirius_sdk.agent.ledger import Schema, SchemaFilters, CredentialDefinition
from sirius_sdk.errors.indy_exceptions import AnoncredsMasterSecretDuplicateNameError, WalletItemAlreadyExists
from sirius_sdk.agent.aries_rfc.feature_0036_issue_credential.messages import ProposedAttrib

from didcomm.const import MSG_TYP_GOSSYP
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
    try:
        await sirius_sdk.NonSecrets.add_wallet_record(
            type_=CONNECTIONS_TYPE, id_=tags['their_did'], value=json.dumps(p2p.metadata),
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


async def issue_cred(their_did: str, values: dict, cred_def_id: str):
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
        comment='Hello Iam issuer',
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


async def foreground():
    try:
        await sirius_sdk.AnonCreds.prover_create_master_secret(MASTER_SECRET_ID)
    except AnoncredsMasterSecretDuplicateNameError as e:
        pass
    my_endpoint = await get_my_endpoint()
    dkms = await sirius_sdk.ledger(DKMS_NETWORK)
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
        else:
            pass

