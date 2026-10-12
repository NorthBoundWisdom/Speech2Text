from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    import tomllib as tomllib
else:
    import tomli as tomllib  # noqa: F401

__all__ = ["tomllib"]
