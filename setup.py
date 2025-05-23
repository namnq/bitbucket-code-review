"""
Setup script for Bitbucket Galaxy Code Review.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bitbucket-galaxy-code-review",
    version="0.1.0",
    author="Galaxy Code Review Team",
    author_email="galaxy@example.com",
    description="An intelligent code review assistant for Bitbucket Cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/galaxy/bitbucket-code-review",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "pyyaml>=5.4.0",
        "openai>=0.27.0",
    ],
    entry_points={
        "console_scripts": [
            "galaxy-review=galaxy_code_review.main:main",
        ],
    },
)