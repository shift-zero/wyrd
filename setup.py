from setuptools import setup, find_packages

setup(
    name="wyrd",
    version="0.1.0",
    packages=find_packages(where="."),
    package_dir={"": "."},
    entry_points={
        "console_scripts": [
            "wyrd=src.__main__:main",
        ],
    },
    python_requires=">=3.11",
)
