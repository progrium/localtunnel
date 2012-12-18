#!/usr/bin/env python
import os
from setuptools import setup, find_packages

from localtunnel import VERSION

setup(
    name='localtunnel',
    version=VERSION,
    author='Jeff Lindsay',
    author_email='progrium@gmail.com',
    description='',
    packages=find_packages(),
    install_requires=['eventlet', 'requests'],
    data_files=[],
    entry_points={
        'console_scripts': [
            'localtunnel-beta = localtunnel.client:run',
            'localtunneld = localtunnel.server:run',]},
)
