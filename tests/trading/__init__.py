# Marks tests/trading as a package so `from .conftest import ...` resolves to
# this directory's shared builders. tests/ itself is deliberately not a package
# (see tests/vision/conftest.py), so making only this subdirectory a package
# keeps the trading helpers importable without a global `conftest` name clash.
