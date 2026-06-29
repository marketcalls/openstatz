#!/usr/bin/env python
"""Export the OpenStatz API OpenAPI schema to app/src/api/openapi.json.

The web workspace turns this into TypeScript types:

    npx openapi-typescript app/src/api/openapi.json -o app/src/api/types.ts

Run:  python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from openstatz.app.server import create_app

    app = create_app()
    schema = app.openapi()

    out = ROOT / "app" / "src" / "api" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(schema.get('paths', {}))} paths, "
          f"{len(schema.get('components', {}).get('schemas', {}))} schemas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
