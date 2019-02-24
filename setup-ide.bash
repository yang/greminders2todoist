#!/usr/bin/env bash

set -o errexit -o nounset


typeshed="$( python -c "import mypy; print(mypy.__file__.replace('__init__.py','typeshed'))" )"
ln -sf "$typeshed/" ./
