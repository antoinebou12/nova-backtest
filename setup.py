import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="novalabs",
    version="0.5.71",
    author="Nova Labs",
    author_email="devteam@novalabs.ai",
    description="Nova Labs aims to facilitate the development of algorithmic trading and this package help to backtest and productionize technical strategies on Crypto Market",
    url="https://github.com/Nova-DevTeam/nova-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    setup_requires=['setuptools_scm']
)
