"""Html九尾狐 local HTTP interface v1.

Endpoints include health/capabilities, project CRUD, Canvas Schema v1 snapshots,
persistent jobs, diagnostics, generation, feedback, templates, alliance skills, and output files.
"""

from .app import serve  # noqa: F401
