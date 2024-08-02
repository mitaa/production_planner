from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='Production Planner',
    version='0.1.0',
    description="A production planner for Satisfactory",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/mitaa/production_planner",
    author="mitaa",
    author_email="mitaa.ceb@gmail.com",
    classifiers=[
        'Development Status :: 3 - Alpha',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MPL 2 License",
        "Operating System :: OS Independent"
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    data_files=[("src", ["production_buildings.json"])],
    python_requires='>=3.10, <4',
    install_requires=[
        "textual",
        "rich",
        "appdirs",
        "pyaml",
    ],
    entry_points={
        'console_scripts': [
            'production_planner=production_planner:main',
        ],
    },
)
