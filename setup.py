"""
Setup configuration for YNAB CSV Parser package.

Enables installation via: pip install -e .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="ynab-csv-parser",
    version="2.0.0",
    description="Comprehensive YNAB integration tool with CSV parsing and API client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="YNAB Parser Contributors",
    url="https://github.com/yourusername/ynab-csv-parser",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "telegram": [
            "python-telegram-bot>=20.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ynab-process=ynab_parser.process:main",
            "ynab-upload=ynab_parser.upload:main",
            "ynab-setup=ynab_parser.setup:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="ynab budget csv parser api",
)
