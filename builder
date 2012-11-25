#!/bin/bash
cp -a . ~
(cd $HOME ; [ ! -d env ] && virtualenv env)

. $HOME/env/bin/activate

pip install -r requirements.txt
python setup.py install
cp -Rf * $HOME/
