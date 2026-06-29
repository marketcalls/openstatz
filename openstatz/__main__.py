#!/usr/bin/env python
#
# Lets you run the CLI without the installed console script, e.g.:
#   python -m openstatz serve --port 8200
#
# Licensed under the Apache License, Version 2.0.

from openstatz.app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
