# AIP Specification

This directory contains the formal specification of the Agent Interaction Protocol.

## Contents

| File | Description |
|------|-------------|
| [specification.md](specification.md) | Full protocol specification (RFC-style) |
| [openapi.yaml](openapi.yaml) | OpenAPI 3.1 description of AIP endpoints |
| [schemas/](schemas/) | JSON Schema files for all protocol types |
| [versions/](versions/) | Version-specific changelogs |

## JSON Schemas

| Schema | Validates |
|--------|-----------|
| [message.schema.json](schemas/message.schema.json) | `AIPMessage` — the message envelope |
| [ack.schema.json](schemas/ack.schema.json) | `AIPAck` — the acknowledgment response |
| [status.schema.json](schemas/status.schema.json) | `AgentStatus`, `RecursiveStatusNode`, `GroupStatus` |

## Using the Schemas

### Python (jsonschema)

```python
import json
import jsonschema

with open("schemas/message.schema.json") as f:
    schema = json.load(f)

message = {"version": "1.0", "message_id": "...", "from": "user", "to": "agent", "action": "assign_task", "intent": "..."}
jsonschema.validate(message, schema)
```

### JavaScript

```javascript
import Ajv from "ajv";
import schema from "./schemas/message.schema.json";

const ajv = new Ajv();
const validate = ajv.compile(schema);
const valid = validate(message);
```

### CLI (ajv-cli)

```bash
npx ajv validate -s schemas/message.schema.json -d message.json
```
