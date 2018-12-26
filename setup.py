#!/usr/bin/env python
from setuptools import setup, find_packages
import pathlib
import versioneer

here = pathlib.Path(__file__).parent


def read(f):
    return (here / f).read_text("utf-8").strip()


setup(
    name="knighted",
    version=versioneer.get_version(),
    author="Xavier Barbosa",
    author_email="clint.northwood@gmail.com",
    description="inject dependencies",
    long_description=read("README.rst"),
    packages=find_packages(),
    install_requires=["cached_property"],
    extras_require={},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=["dependency injection", "composing"],
    url="http://lab.errorist.xyz/abc/knighted",
    license="MIT",
    cmdclass=versioneer.get_cmdclass(),
)
