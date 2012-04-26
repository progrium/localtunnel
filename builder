#!/bin/bash
cp -a . ~
cd
(cat <<-EOF
  pip install -r requirements.txt
  python setup.py develop
  python -c "__requires__ = 'ginkgo'; import sys; from pkg_resources import load_entry_point; sys.exit(load_entry_point('ginkgo','console_scripts', 'ginkgo')())" ./config/dotcloud.conf.py
EOF
) > run
chmod a+x run
