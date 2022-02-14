import json

import sirius_sdk


IDENTITIES_TYPE = 'demo_identities'


async def get_my_endpoint():
    endpoints = await sirius_sdk.endpoints()
    my_endpoint = [e for e in endpoints if e.routing_keys == []][0]
    return my_endpoint


async def create_identity(label: str) -> (str, str):
    """
    Create new Identity is SSI world

    :param label: human-readable presentation
    :return: DID, invitation-string
    """
    did, verkey = await sirius_sdk.DID.create_and_store_my_did()
    my_endpoint = await get_my_endpoint()
    inv = sirius_sdk.aries_rfc.Invitation(
        label=label,
        recipient_keys=[verkey],
        endpoint=my_endpoint.address
    )
    inv_s = inv.invitation_url
    js = {'did': did, 'inv': inv_s, 'label': label}
    await sirius_sdk.NonSecrets.add_wallet_record(
        type_=IDENTITIES_TYPE, id_=did, value=json.dumps(js),
        tags=js
    )
    return did, inv_s
