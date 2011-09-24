#!/usr/bin/env python
import os
from setuptools import setup, find_packages

setup(
    name='localtunnel',
    version='0.4.0',
    author='Jeff Lindsay',
    author_email='jeff.lindsay@twilio.com',
    description='',
    packages=find_packages(),
    install_requires=['gservice', 'ws4py'],
    data_files=[],
)
