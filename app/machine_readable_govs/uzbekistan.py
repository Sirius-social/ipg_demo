doc = {
  "@context": ["https://github.com/hyperledger/aries-rfcs/blob/main/concepts/0430-machine-readable-governance-frameworks/context.jsonld"],
  "name": "Uzbekistan Gov Framework",
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
    "Uzbekistan",
  ],
  "geos": [
    "UZB"
  ],
  "schemas": [
    {
      "id": "Gk6YNB9x5w6FwhNBUKjUEY:2:Trade-License:1.0",
      "name": "Trade Licence",
    },
    {
      "id": "9MG2vmFLem8p4VBmcu3DRV:2:Tax-Payer:1.0",
      "name": "Tax Payer license",
    }
  ],
  "cred_defs": [
      {
        "id": "Nj3ejq7qjAKdtHDuS9d6Nm:3:CL:9164:EXPORTER",
        "name": "Exporter License"
      }
  ],
  "participants": [
    {
      "name": "gov_uzb_trading_ministry",
      "id": "did:sov:Nj3ejq7qjAKdtHDuS9d6Nm",
      "describe": {
        "label": "Uzbekistan Trade Ministry",
        "website": "issuinggovernmentsite.org",
        "email": "credential_manager@issuinggovernmentsite.org"
      }
    },
    {
      "name": "gov_uzb_taxes_ministry",
      "id": "did:sov:2yWjzFtsDeFn8CJxZURwvN",
      "describe": {
        "label": "Uzbekistan Taxes Ministry",
        "website": "issuinglabsite.com",
        "email": "credential_manager@issuinglabsite.com"
      }
    },
    {
      "name": "uzb_sulfur_manufacturer",
      "id": "did:sov:PsEdPi5wHfHyJEEyCUJnni",
      "describe": {
        "label": "JSC UZBEKNEFTEGAZ",
        "website": "issuinggovernmentsite.org",
        "email": "credential_manager@issuinggovernmentsite.org"
      }
    }
  ],
  "roles": [
    "trader",
    "exporter",
    "licenser"
  ],
  "permissions": [ 
    {
      "grant": ["trader"],
      "when": {
        "and": [
          {"schema": "Trade Licence", "issuer": "gov_uzb_trading_ministry"},
          {"schema": "Tax Payer license", "issuer": "gov_uzb_taxes_ministry"},
        ]
      }
    },
    {
      "grant": ["licenser"],
      "when": {
        "any": [
          {"id": "did:sov:PsEdPi5wHfHyJEEyCUJnni"}
        ]
      }
    },
    {
      "grant": ["exporter"],
      "when": {
        "any": [
          {"cred_def": "Exporter License"}
        ]
      }
    }
  ]
}