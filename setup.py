import os
from setuptools import setup, find_packages

# Read version from version.py
about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "research_agent", "version.py"), "r", encoding="utf-8") as f:
    exec(f.read(), about)

# Read README.md for long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="research-agent",
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=about["__url__"],
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "gradio>=4.0.0",
        "markdown>=3.0.0",
        # Add your other dependencies here
    ],
)
