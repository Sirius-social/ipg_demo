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
    "Russian Federation",
  ],
  "geos": [
    "RUS"
  ],
  "schemas": [
    {
      "id": "VbNrngVsD113FC5gWsHsC2:2:DualPurposeLicense:1.0",
      "name": "Permission for licensing cargoes of the 2nd destination",
    },
    {
      "id": "46rZgNsTms48s7wz7RqwHy:2:Cargo-License:2.0",
      "name": "Permit of the Ministry of Industry and Trade",
    }
  ],
  "participants": [
    {
      "name": "gov_border_service",
      "id": "did:sov:VbNrngVsD113FC5gWsHsC2",
      "describe": {
        "label": "Border Service",
        "website": "issuinggovernmentsite.org",
        "email": "credential_manager@issuinggovernmentsite.org"
      }
    },
    {
      "name": "gov_trade_ministry",
      "id": "did:sov:46rZgNsTms48s7wz7RqwHy",
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
