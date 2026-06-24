"""Packaged SQL migrations for the stockroom warehouse.

This package exists so the migration ``.sql`` files ship and resolve with the
installed ``stockroom`` package (located via ``stockroom.migrations``'s
directory). The files are plain SQL executed by the migration framework
(milestone 2); this package holds no runtime Python behavior.
"""

from __future__ import annotations
