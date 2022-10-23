import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fr3d-python-adapter",
    version="1.0",
    author="Tomasz Zok",
    author_email="tomasz.zok@cs.put.poznan.pl",
    description="An adapter for fr3d-python, which reads an mmCIF file and produces a unified list of RNA interactions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tzok/fr3d-python-adapter",
    project_urls={
        "Bug Tracker": "https://github.com/tzok/fr3d-python-adapter/issues",
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable', 'Environment :: Console',
        'Intended Audience :: Science/Research', 'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent', 'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        'orjson==3.6.*', 'fr3d @ git+https://github.com/tzok/fr3d-python', 'barnaba==0.1.7', 'Flask==2.1.*',
        'mmcif==0.79'
    ],
    entry_points={'console_scripts': ['fr3d-python-adapter=fr3d_python_adapter.adapter:main']})
