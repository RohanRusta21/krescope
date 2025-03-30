from setuptools import setup, find_packages

setup(
    name="k8s-recommender",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "kubernetes>=24.0",
        "rich>=13.0",
        "typing-extensions>=4.0"  # For TypedDict support in older Python
    ],
    entry_points={
        "console_scripts": [
            "krescope=recommender.cli:cli"
        ]
    },
    python_requires=">=3.8",
)