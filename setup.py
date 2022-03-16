import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="novalabs",
    version="0.0.6",
    author="Nova Labs",
    author_email="devteam@novalabs.ai",
    description="Nova API & Exchange client",
    url="https://github.com/Nova-DevTeam/nova-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)