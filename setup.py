from setuptools import setup, find_packages

setup(
    name="garjus",
    version="1.2.1",
    author="Brian D. Boyd",
    author_email="brian.d.boyd@vumc.org",
    description="Python package for managing imaging research projects in REDCap and XNAT",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ccmvumc/garjus",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    install_requires=[
        "pandas",
        "pycap",
        "pyxnat",
        "dax",
        "click",
        "sphinx",
        "pydot",
        "plotly",
        "dash_bootstrap_components",
        "dash_bootstrap_templates",
    ],
    entry_points={"console_scripts": ["garjus = garjus.cli:cli"]},
)
