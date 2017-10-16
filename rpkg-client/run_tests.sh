#!/bin/sh
PYTHONPATH=.:$PYTHONPATH python2 -m pytest tests -s $@
