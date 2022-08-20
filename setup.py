import re
import ast
from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('nova/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1))) + str(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="novalabs",
    version=version,
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
