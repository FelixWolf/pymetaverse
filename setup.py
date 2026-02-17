from setuptools import setup, find_packages
from metaverse import __version__ as version

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="Metaverse",
    version=version,
    description="A library for handling Second Life things.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FelixWolf/pymetaverse",
    author="Félix",
    author_email="felix.wolfz@gmail.com",
    packages=find_packages(exclude=("build","examples")) + ["metaverse.viewer.message_template"],
    package_data={
        "metaverse.viewer.message_template": [
            "*.msg", "*.msg.sha1", "*.txt"
        ],
    },
    license="Zlib",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries"
    ]
)