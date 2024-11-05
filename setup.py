from setuptools import setup, find_packages

setup(
    name="tooldantic",
    version="0.1.0",
    description="An extension of pydantic for use LLM tool calling and structured outputs.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Nicholas Barker",
    author_email="nick@agientic.ai",
    url="https://github.com/nicholishen/tooldantic",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pydantic>=2.0,<3.0",
        "docstring-parser",
    ],
    extras_require={
        "openai": ["openai>=1.40.0"],
    },
    include_package_data=True,
)
