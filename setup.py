#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=6.0', 'lxml==4.3.0', 'mypy', 'typing-extensions==3.7.2', 'todoist-python==7.0.19',
                'google_auth==1.6.2']

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Yang Zhang",
    author_email='yaaang@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Migrate Google Reminders (including Google Inbox Reminders) to Todoist",
    entry_points={
        'console_scripts': [
            'greminders2todoist=greminders2todoist.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='greminders2todoist',
    name='greminders2todoist',
    packages=find_packages(include=['greminders2todoist']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/yang/greminders2todoist',
    version='0.1.0',
    zip_safe=False,
    extras_require={
        'test': setup_requirements + test_requirements,
        'dev': [
            'ipython[notebook]==7.2.0',
            'ipdb==0.11',
        ]
    }
)
