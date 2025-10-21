from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="retro",
    version="1.0.0",
    author="xrce",
    description="Retro Game Package Manager",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xrce/retro",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests",
        "tqdm",
        "beautifulsoup4",
        "py7zr",
        "rarfile",
    ],
    entry_points={
        "console_scripts": [
            "retro=retro:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
