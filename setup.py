from setuptools import setup, find_namespace_packages
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
    packages=find_namespace_packages(),
    include_package_data=True,
    package_data={
        "metaverse.viewer": [
            "message_template/*",
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