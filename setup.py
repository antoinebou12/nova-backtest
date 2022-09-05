import json
import urllib3
from distutils.version import StrictVersion
from setuptools import setup, find_packages

lib3 = urllib3.PoolManager()


def versions(package_name):
    url = "https://pypi.org/pypi/%s/json" % (package_name,)
    data = json.load(lib3.urlopen('GET', lib3.request('GET', url)))
    _versions = data["releases"].keys()
    _versions.sort(key=StrictVersion)
    return _versions


package_version = versions('novalabs')
VERSION = package_version[:-1] + str(int(package_version[-1])+1)

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
