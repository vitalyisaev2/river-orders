#!/usr/bin/env python3
# encoding: utf-8

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    reqs = f.read().splitlines()

setup(
    name="river-orders",
    version="0.1.0",
    author="Vitaly Isaev",
    author_email="vitalyisaev2@gmail.com",
    maintainer="Vitaly Isaev",
    maintainer_email="vitalyisaev2@gmail.com",
    url="https://github.com/vitalyisaev2/river-orders",
    description="Tool for building river network graph",
    long_description="""
Simple tool for building river network graph from data
published in USSR Surface water resources""",
    license="commercial",
    platforms=["Linux"],
    include_package_data=True,
    zip_safe=False,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'river-orders-build=river_orders:build_river_network',
        ]},
    data_files=[
        ('/usr/bin/', ['scripts/river-orders-prepare-data']),
    ],
    install_requires=reqs,
)
