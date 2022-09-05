import re
import ast
import json
import urllib2
from setuptools import setup, find_packages

def versions(package_name):
    url = "https://pypi.org/pypi/%s/json" % (package_name,)
    data = json.load(urllib2.urlopen(urllib2.Request(url)))
    versions = data["releases"].keys()
    versions.sort(key=StrictVersion)
    return versions

package_version = versions('novalabs')
VERSION=package_version[:-1] + str(int(package_version[-1])+1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="novalabs",
    version=VERSION,
    author="Nova Labs",
    author_email="devteam@novalabs.ai",
    description="Wrappers around Nova Labs utilities focused on safety and testability",
    long_description=long_description,
    url="https://github.com/Nova-DevTeam/nova-python",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    setup_requires=['setuptools_scm']
)
