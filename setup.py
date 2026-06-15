from setuptools import setup, find_packages
from pathlib import Path

DESCRIPTION = 'Interface for predicting and mapping benthic habitat (substrates) from any side-scan sonar mosaic.'
LONG_DESCRIPTION = Path('README.md').read_text()

exec(open('mayamapper/version.py').read())

setup(
    name="mayamapper",
    version=__version__,
    author="Cameron Bodine",
    author_email="bodine.cs@gmail.email",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    package_data={"mayamapper": ["conda/*.yml"]},
    # data_files=[("pingmapper_config", ["pingmapper/default_params.json"])],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Scientific/Engineering :: Oceanography",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Hydrology"
        ],
    keywords=[
        "pingmapper",
        "sonar",
        "ecology",
        "remotesensing",
        "sidescan",
        "sidescan-sonar",
        "aquatic",
        "humminbird",
        "lowrance",
        "gis",
        "oceanography",
        "limnology",],
    python_requires="<3.13",
    install_requires=['pinginstaller', 'pingwizard'],
    project_urls={
        "Issues": "https://github.com/PINGEcosystem/MayaMapper/issues",
        "GitHub":"https://github.com/PINGEcosystem/MayaMapper",
        # "Homepage":"https://PINGEcosystem.github.io/HabiMapper/",
    },
)