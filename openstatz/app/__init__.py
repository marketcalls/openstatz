#!/usr/bin/env python
#
# OpenStatz — optional FastAPI service layer.
#
# This subpackage is only required for `pip install openstatz[app]`. The core
# library never imports it, and importing this package does NOT pull in FastAPI
# until a server entry point is actually called.
#
# Licensed under the Apache License, Version 2.0.
