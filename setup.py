#!/usr/bin/env python
from setuptools import setup, find_packages
import versioneer

setup(
    name='knighted',
    version=versioneer.get_version(),
    author='Xavier Barbosa',
    author_email='clint.northwood@gmail.com',
    description='inject dependencies',
    packages=find_packages(),
    install_requires=[],
    extras_require={
        ':python_version=="3.3"': ['asyncio'],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    keywords=['dependency injection', 'composing'],
    url='http://lab.errorist.xyz/abc/knighted',
    license='MIT',
    cmdclass=versioneer.get_cmdclass()
)
