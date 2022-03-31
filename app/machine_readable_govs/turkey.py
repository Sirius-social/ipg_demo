doc = {
  "@context": ["https://github.com/hyperledger/aries-rfcs/blob/main/concepts/0430-machine-readable-governance-frameworks/context.jsonld"],
  "name": "Turkey Gov Framework",
  "version": "0.2",
  "format": "1.0",
  "id": "<uuid>",
  "description": "<TODO>",
  "last_updated": "2022-10-01",
  "docs_uri": "need_to_create",
  "data_uri": "need_to_create",
  "topics": [
    "trading, manufacturing"
  ],
  "jurisdictions": [
    "Turkey",
  ],
  "geos": [
    "TK"
  ],
  "schemas": [
    {
      "id": "2QLCb1LX6w5DAWqZj8Uq6A:2:Dual Purpose License:1.0",
      "name": "Permission for licensing cargoes of the 2nd destination",
    },
    {
      "id": "HahGzAQHe413h6np218TEx:2:Trading License:1.0",
      "name": "Permit of the Ministry of Industry and Trade",
    }
  ],
  "participants": [
    {
      "name": "gov_border_service",
      "id": "did:sov:2QLCb1LX6w5DAWqZj8Uq6A",
      "describe": {
        "label": "Border Service",
        "website": "issuinggovernmentsite.org",
        "email": "credential_manager@issuinggovernmentsite.org"
      }
    },
    {
      "name": "gov_trade_ministry",
      "id": "did:sov:HahGzAQHe413h6np218TEx",
      "describe": {
        "label": "Trading Ministry",
        "website": "issuinglabsite.com",
        "email": "credential_manager@issuinglabsite.com"
      }
    }
  ],
  "roles": [
    "trader",
    "dual_purpose_cargo_licenser"
  ],
  "permissions": [
    {
      "grant": ["trader"],
      "when": {
        "and": [
          {"schema": "Permit of the Ministry of Industry and Trade", "issuer": "gov_trade_ministry"},
        ]
      }
    },
    {
      "grant": ["dual_purpose_cargo_licenser"],
      "when": {
        "any": [
          {"schema": "Permission for licensing cargoes of the 2nd destination", "issuer": "gov_border_service"},
        ]
      }
    }
  ]
}
