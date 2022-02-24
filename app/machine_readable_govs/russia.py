doc = {
  "@context": ["https://github.com/hyperledger/aries-rfcs/blob/main/concepts/0430-machine-readable-governance-frameworks/context.jsonld"],
  "name": "Russian Gov Framework",
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
      "name": "Разрешение на лицензирование грузов 2-го назначения",
    },
    {
      "id": "46rZgNsTms48s7wz7RqwHy:2:Cargo-License:2.0",
      "name": "Разрешение Мин.пром.торга",
    }
  ],
  "participants": [
    {
      "name": "gov_rus_border_service",
      "id": "did:sov:VbNrngVsD113FC5gWsHsC2",
      "describe": {
        "label": "Погран. Служба РФ",
        "website": "issuinggovernmentsite.org",
        "email": "credential_manager@issuinggovernmentsite.org"
      }
    },
    {
      "name": "gov_rus_trade_ministry",
      "id": "did:sov:46rZgNsTms48s7wz7RqwHy",
      "describe": {
        "label": "Мин. торговли РФ",
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
          {"schema": "Разрешение Мин.пром.торга", "issuer": "gov_rus_trade_ministry"},
        ]
      }
    },
    {
      "grant": ["dual_purpose_cargo_licenser"],
      "when": {
        "any": [
          {"schema": "Разрешение на лицензирование грузов 2-го назначения", "issuer": "gov_rus_border_service"},
        ]
      }
    }
  ]
}
