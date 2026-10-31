"""Headless Excel file I/O for pyre -- requires the 'excel' optional extra (openpyxl).

Never imported by pyre/__init__.py: a bare `import pyre` must not require
openpyxl. Only `from pyre.io_excel import ...` does.
"""
