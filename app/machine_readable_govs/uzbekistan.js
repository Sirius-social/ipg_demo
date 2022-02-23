DOC = {
  "@context": ["https://github.com/hyperledger/aries-rfcs/blob/main/concepts/0430-machine-readable-governance-frameworks/context.jsonld"],
  "name": "Uzbekistan Trading License",
  "version": "0.2",
  "format": "1.0",
  "id": "<uuid>",
  "description": "This document describes COVID health and travel governance for the nation of Aruba in a machine readable way.",
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
      "id": "4CLG5pU5v294VdkMWxSByZ:2:Email:1.0",
      "name": "Validated Email",
    },
    {
      "id": "4CLG5pU5v294VdkMWxSByZ:2:SMS:1.0",
      "name": "SMS",
    },
    {
      "id": "4CLG5pU5v294VdkMWxSByZ:2:Medical_Release:1.0",
      "name": "Medical Release",
    },
    {
      "id": "RuuJwd3JMffNwZ43DcJKN1:2:Lab_Order:1.4",
      "name": "Lab Order",
    },
    {
      "id": "RuuJwd3JMffNwZ43DcJKN1:2:Lab_Result:1.4",
      "name": "Lab Result",
    },
    {
      "id": "RuuJwd3JMffNwZ43DcJKN1:2:Vaccine:1.4",
      "name": "Vaccine",
    },
    {
      "id": "RuuJwd3JMffNwZ43DcJKN1:2:Vaccine_Exemption:1.4",
      "name": "Vaccine Exemption",
    },
    {
      "id": "RuuJwd3JMffNwZ43DcJKN1:2:Trusted_Traveler:1.4",
      "name": "Trusted Traveler",
    }
  ],
  "participants": [
    {
      "name": "Aruba Government",
      "id": "J1pp5Ro5Xf6qtF281xknFs",
      "describe": {
        "label": "Aruba",
        "sublabel": "Aruba Government",
        "website": "issuinggovernmentsite.org",
        "email": "credential_manager@issuinggovernmentsite.org"
      }
    },
    {
      "name": "General Horacio Oduber Hospital of Aruba",
      "id": "FK8a5myo4jhh3yDfn4WtbS",
      "describe": {
        "label": "Horacio Oduber Hospital",
        "sublabel": "General Horacio Oduber Hospital of Aruba",
        "website": "issuinglabsite.com",
        "email": "credential_manager@issuinglabsite.com"
      }
    },
    {
      "name": "Hilton Casino",
      "id": "did:example:casino",
      "describe": {
        "label": "Hilton Resort and Casino",
        "sublabel": "Verifying Org",
        "website": "verifyingorgsite.com",
        "email": "verifying_manager@verifyingorgsite.com"
      }
    }
  ],
  "roles": [
    "holder",
    "health_issuer",
    "travel_issuer",
    "health_verifier",
    "travel_verifier",
    "hospitality_verifier"
  ],
  "permissions": [ # Roles mapped to participants
    {
      "grant": ["health_issuer"],
      "when": {
        "any": [
          {"id": "FK8a5myo4jhh3yDfn4WtbS"},
          {"id": "did:example:lab"}
        ]
      }
    },
    {
      "grant": ["travel_issuer"],
      "when": {
        "any": [
          {"id": "J1pp5Ro5Xf6qtF281xknFs"}
        ]
      }
    },
    {
      "grant": ["health_verifier"],
      "when": {
        "any": [
          {"id": "J1pp5Ro5Xf6qtF281xknFs"}
        ]
      }
    },
    {
      "grant": ["travel_verifier"],
      "when": {
        "any": [
          {"id": "J1pp5Ro5Xf6qtF281xknFs"}
        ]
      }
    },
    {
      "grant": ["hospitality_verifier"],
      "when": {
        "any": [
          {"id": "did:example:casino"}
        ]
      }
    }
  ],
  "actions": [
  // Actions are a name associated with a protocol (and sometimes a schema)
    {
      "name": "connect",
      "protocol": "https://didcomm.org/connections/1.0/",
      "startmessage": "invitation",
      "details": {}
    },

    {
      "name": "issue_lab_order",
      "protocol": "https://didcomm.org/issue-credential/1.0/",
      "startmessage": "offer-credential",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Lab_Order:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "issue_lab_result",
      "protocol": "https://didcomm.org/issue-credential/1.0/",
      "startmessage": "offer-credential",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Lab_Result:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "issue_vaccine",
      "protocol": "https://didcomm.org/issue-credential/1.0/",
      "startmessage": "offer-credential",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Vaccination:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "issue_vaccine_exemption",
      "protocol": "https://didcomm.org/issue-credential/1.0/",
      "startmessage": "offer-credential",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Vaccine_Exemption:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "issue_trusted_traveler",
      "protocol": "https://didcomm.org/issue-credential/1.0/",
      "startmessage": "offer-credential",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Trusted_Traveler:1.4",
        "presentation_definition": "http://localhost:3100/api/presentation-exchange" // Development only, replace with a hashlink in production
      }
    },
    {
      "name": "verify_identity",
      "protocol": "https://didcomm.org/present-proof/1.0/",
      "startmessage": "request-presentation",
      "details": {}
    },
    {
      "name": "verify_lab_order",
      "protocol": "https://didcomm.org/present-proof/1.0/",
      "startmessage": "request-presentation",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Lab_Order:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "verify_lab_result",
      "protocol": "https://didcomm.org/present-proof/1.0/",
      "startmessage": "request-presentation",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Lab_Result:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "verify_vaccine",
      "protocol": "https://didcomm.org/present-proof/1.0/",
      "startmessage": "request-presentation",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Vaccination:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "verify_vaccine_exemption",
      "protocol": "https://didcomm.org/present-proof/1.0/",
      "startmessage": "request-presentation",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Vaccine_Exemption:1.4",
        "presentation_definition": "hl:zm9YZpCjPLPJ4Epc:z3TSgaEFFHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPUJFDD" // Example, not real
      }
    },
    {
      "name": "verify_trusted_traveler",
      "protocol": "https://didcomm.org/present-proof/1.0/",
      "startmessage": "request-presentation",
      "details": {
        "schema": "RuuJwd3JMffNwZ43DcJKN1:2:Trusted_Traveler:1.4",
        "presentation_definition": [
          {
            "travel_verifier": "hl:zm9YZpCjPLPJ4Epc:z3TSgXTuaHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPQyLHy"
          },
          {
            "hospitality_verifier": "hl:zm9YZpCjPLPJ4Epc:z3TSgXTuaHxY2tsArhUreJ4ixgw9NW7DYuQ9QTPQyLHy"
          }
        ]
      }
    }
  ],
  "privileges": [ // Actions mapped to roles
    {
      "grant": [
        "issue_lab_order"
      ],
      "when": {
        "any": [
          {
            "role": "health_issuer"
          }
        ]
      }
    },
    {
      "grant": [
        "issue_lab_result"
      ],
      "when": {
        "any": [
          {
            "role": "health_issuer"
          }
        ]
      }
    },
    {
      "grant": [
        "issue_vaccine"
      ],
      "when": {
        "any": [
          {
            "role": "health_issuer"
          }
        ]
      }
    },
    {
      "grant": [
        "issue_vaccine_exemption"
      ],
      "when": {
        "any": [
          {
            "role": "health_issuer"
          },
          {
            "role": "holder"
          }
        ]
      }
    },
    {
      "grant": [
        "issue_trusted_traveler"
      ],
      "when": {
        "any": [
          {
            "role": "travel_issuer"
          }
        ]
      }
    },
    {
      "grant": [
        "verify_identity"
      ],
      "when": {
        "any": [
          {
            "role": "health_issuer"
          },
          {
            "role": "travel_issuer"
          },
          {
            "role": "health_verifier"
          },
          {
            "role": "travel_verifier"
          },
          {
            "role": "hospitality_verifier"
          }
        ]
      }
    },
    {
      "grant": [
        "verify_lab_order"
      ],
      "when": {
        "any": [
          {
            "role": "health_verifier"
          }
        ]
      }
    },
    {
      "grant": [
        "verify_lab_result"
      ],
      "when": {
        "any": [
          {
            "role": "health_verifier"
          }
        ]
      }
    },
    {
      "grant": [
        "verify_vaccine"
      ],
      "when": {
        "any": [
          {
            "role": "health_verifier"
          }
        ]
      }
    },
    {
      "grant": [
        "verify_vaccine_exemption"
      ],
      "when": {
        "any": [
          {
            "role": "health_verifier"
          }
        ]
      }
    },
    {
      "grant": [
        "verify_trusted_traveler"
      ],
      "when": {
        "any": [
          {
            "role": "travel_verifier"
          },
          {
            "role": "hospitality_verifier"
          }
        ]
      }
    }
  ],
  "flows": {
  // Most likely a stand-alone document referred to
  // using a hash link, but included here while we're brainstorming
    "connect-to-health-issuer": {
      "role": "holder",
      "initial": true,
      "actions": [
        {
          "name": "connect",
          "target": "health_issuer"
        }
      ],
      "next": [
        "success": [
          {
            "name": "health-verify-identity", // Happy path
          },
        ]
      ]
    }
    "health-verify-identity": {
      "role": "health_issuer",
      "initial": true,
      "conditions": [
        {
          "type": "connection",
          "target": "holder"
        }
      ],
      "actions": [
        {
          "name": "verify_identity",
        },
      ],
      "next": [
        "success": [
          {
            "name": "health-issue-credential", // Happy path
          },
        ]
      ]
    },
    "health-issue-credential": {
      "role": "health_issuer",
      "actions": [
        "or": [
          {
            "and": [
              { "name": "issue_lab_order" },
              { "name": "issue_lab_result" }
            ]
          },
          { "name": "issue_vaccine" },
          { "name": "issue_vaccine_exemption" },
        ]
      ],
      "next": [
        "success": [
          {
            "name": "connect-to-travel-issuer" // Happy path
          },
        ]
      ]
    },
    "connect-to-travel-issuer": {
      "role": "holder",
      "actions": [
        {
          "name": "connect",
          "target": "travel_issuer"
        }
      ],
      "next": [
        "success": [
          {
            "name": "travel-verify-holder" // Happy path
          }
        ]
      ]
    },
    "travel-verify-holder": {
      "role": "travel_issuer",
      "actions": [
        {
          "name": "verify_identity",
        },
      ],
      "next": [
        "success": [
          {
            "name": "travel-issue-credential", // Happy path
          },
        ]
      ]
    },
    "travel-issue-credential": {
      "role": "travel_issuer",
      "actions": [
        {
          "name": "issue_trusted_traveler"
        }
      ],
    },
  }
}