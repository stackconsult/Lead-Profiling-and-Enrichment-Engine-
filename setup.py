"""
Setup script for the Lead Profiling and Enrichment Engine
"""

from setuptools import setup, find_packages

setup(
    name="lead-profiling-engine",
    version="0.1.0",
    description="Lead Profiling and Enrichment Engine - Research, profile and grade leads",
    author="Stack Consult",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
