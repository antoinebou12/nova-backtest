import requests
from setuptools import setup, find_packages


def versions(package_name):
    data = requests.get(f'https://pypi.python.org/pypi/{package_name}/json')
    _versions = data.json()['releases'].keys()
    return list(_versions)[-1]


package_version = versions('novalabs')
VERSION = package_version[:-1] + str(int(package_version[-1])+1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="novalabs",
    version="1.2.63",
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
