#!/usr/bin/env python3
"""
Setup script for DevOps Agent package.
"""

from setuptools import setup, find_packages
import os
import re

with open(os.path.join("src", "__init__.py"), "r", encoding="utf-8") as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    version = version_match.group(1) if version_match else "0.2.0"

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="devops-agent",
    version=version,
    description="AI-powered Docker deployment platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Edge Agents Team",
    author_email="team@example.com",
    url="https://github.com/yourusername/devops-agent",
    packages=find_packages(),
    package_dir={"": "src"},
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    # The CLI is invoked as `python -m src.cli`. No console script is
    # installed by default; a prior entry point targeted a
    # `devops_agent.cli` module that does not exist in this repo.
)
