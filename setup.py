#!/usr/bin/env python

from distutils.core import setup

setup(
    name='tripleo-swift-ring-tool',
    version='0.1',
    description='Some tools for deploying Swift using TripleO',
    author='Christian Schwede',
    author_email='cschwede@redhat.com',
    url='http://www.github.com/cschwede/tripleo-swift-ring-tool',
    packages=['tripleo_swift_ring_tool'],
    scripts=['bin/tripleo-swift-ring-tool'],
)
