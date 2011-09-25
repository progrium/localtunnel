#!/bin/bash
bin/python setup.py develop
bin/python ./scripts/gservice -C ./config/heroku.conf.py