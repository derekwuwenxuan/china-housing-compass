"""Compatibility metadata for older setuptools environments.

Modern builders use ``pyproject.toml``. This file keeps local Python 3.9
environments with older setuptools from producing an ``UNKNOWN`` wheel.
"""

from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).parent


setup(
    name="china-housing-compass",
    version="0.1.0",
    description="Open-source China housing-market analysis and home-purchase assessment toolkit.",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="China Housing Compass contributors",
    license="MIT",
    python_requires=">=3.9",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"china_housing_compass": ["schema.sql", "templates/*.html"]},
    entry_points={"console_scripts": ["china-housing-compass=china_housing_compass.cli:main"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
