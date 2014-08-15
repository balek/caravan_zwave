#!/usr/bin/env python

from setuptools import setup

setup(name='caravan_zwave',
    version='0.0.1',
    description='Z-Wave module for Caravan',
    author='Alexey Balekhov',
    author_email='a@balek.ru',
    py_modules = ['caravan_zwave'],
    entry_points = {
        'autobahn.twisted.wamplet': [ 'zwave = caravan_zwave:AppSession' ]
    })