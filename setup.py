import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="python-novalabs",
    version="0.0.1",
    author="Nova Labs",
    author_email="devteam@novalabs.ai",
    description="Nova API & Exchange client",
    url="https://github.com/Nova-DevTeam/python-nova",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)