from setuptools import setup, find_packages

setup(
    name="k8s-recommender",
    version="0.1",
    packages=find_packages(),
    install_requires=["click", "kubernetes", "rich"],
    entry_points={
        "console_scripts": [
            "krescope=recommender.cli:cli"
        ]
    }
)