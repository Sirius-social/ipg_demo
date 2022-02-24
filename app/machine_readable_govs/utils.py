import logging

import sirius_sdk

from settings import DKMS_NETWORK


async def check_schema(dkms, map_schemas, map_participants, my_did, **kwargs) -> bool:
    try:
        schema = kwargs.get('schema')
        issuer = kwargs.get('issuer')
        schema = map_schemas.get(schema, schema)
        if issuer in map_participants:
            issuer = map_participants[issuer]['id']
        if ':' in issuer:
            issuer = issuer.split(':')[-1]
        print('')
        schema_in_dkms = await dkms.load_schema(schema, my_did)
        print('')
        attr = schema_in_dkms.attributes[0]
        proof_request = {
            "name": "Proof request",
            "nonce": '7513514252',
            "requested_attributes": {
                "attr1_referent": {
                    "name": attr,
                    "restrictions": {
                        "issuer_did": issuer
                    }
                }
            },
            "requested_predicates": {},
            "version": "0.1"
        }
        print('')
        found = await sirius_sdk.AnonCreds.prover_search_credentials_for_proof_req(
            proof_request=proof_request, limit_referents=100
        )
        if found:
            requested_attributes = found.get('requested_attributes', {})
            success = requested_attributes.get('attr1_referent', [])
            if success:
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        logging.exception('Error')
        return False


async def check_id(map_participants, **kwargs) -> bool:
    id_ = kwargs.get('id', None)
    if not id_:
        return False
    if id_ in map_participants.keys():
        p = map_participants[id_]
        test_did = p['id']
    else:
        test_did = id_
    if ':' in test_did:
        test_did = test_did.split(':')[-1]
    try:
        my_dids = await sirius_sdk.DID.list_my_dids_with_meta()
        success = any([item['did'] == test_did for item in my_dids])
        return success
    except Exception as e:
        logging.exception('Error')
        return False


async def check_cred_def(dkms, map_cred_defs, my_did, **kwargs) -> bool:
    cred_def = kwargs.get('cred_def', None)
    if not cred_def:
        return False
    try:
        if cred_def in map_cred_defs:
            cred_def_id = map_cred_defs[cred_def]
        else:
            cred_def_id = cred_def
        print('')
        cred_def_in_dkms = await dkms.load_cred_def(cred_def_id, my_did)
        attr = cred_def_in_dkms.schema.attributes[0]
        proof_request = {
            "name": "Proof request",
            "nonce": '7513514252',
            "requested_attributes": {
                "attr1_referent": {
                    "name": attr,
                    "restrictions": {
                        "cred_def_id": cred_def_id
                    }
                }
            },
            "requested_predicates": {},
            "version": "0.1"
        }
        found = await sirius_sdk.AnonCreds.prover_search_credentials_for_proof_req(
            proof_request=proof_request, limit_referents=100
        )
        if found:
            requested_attributes = found.get('requested_attributes', {})
            success = requested_attributes.get('attr1_referent', [])
            if success:
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        logging.exception('Error')
        return False


async def extract_my_roles(doc: dict) -> list:
    map_schemas = {}
    map_cred_defs = {}
    map_participants = {}
    my_permissions = []
    my_dids = await sirius_sdk.DID.list_my_dids_with_meta()
    my_did = my_dids[0]['did']
    dkms = await sirius_sdk.ledger(DKMS_NETWORK)
    # ==== Schemas ====
    schemas = doc.get('schemas', [])
    for schema_descriptor in schemas:
        id = schema_descriptor.get('id', None)
        name = schema_descriptor.get('name', None)
        if name and id:
            map_schemas[name] = id
    # ==== Cred-Defs ====
    cred_defs = doc.get('cred_defs', [])
    for cred_defs_descriptor in cred_defs:
        id = cred_defs_descriptor.get('id', None)
        name = cred_defs_descriptor.get('name', None)
        if name and id:
            map_cred_defs[name] = id
    # ==== Participants ====
    participants = doc.get('participants', [])
    for item in participants:
        id = item.get('id', None)
        name = item.get('name', None)
        if id:
            map_participants[id] = item
        if name:
            map_participants[name] = item
    # ======= Permissions ============
    permissions = doc.get('permissions', [])
    for perm in permissions:
        grant = perm['grant']
        when = perm['when']
        for cond, items in when.items():
            results = []
            for item in items:
                # iter
                if 'schema' in item.keys():
                    success = await check_schema(dkms, map_schemas, map_participants, my_did, **item)
                elif 'id' in item.keys():
                    success = await check_id(map_participants, **item)
                elif 'cred_def' in item.keys():
                    success = await check_cred_def(dkms, map_cred_defs, my_did, **item)
                else:
                    success = False
                # calc temp result
                if cond == 'any':
                    results.append(success)
                    if success:
                        break
                elif cond == 'and':
                    results.append(success)
                    if not success:
                        break
            if all(results):
                my_permissions.extend(grant)

    return my_permissions
