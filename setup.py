from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='tom_autovar',
    version='0.0.1',
    description='Autovar pipeline for tom_education',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Joe Singleton',
    author_email='joesingo@gmail.com',
    install_requires=[
        'autovar @ git+https://github.com/zemogle/autovar@1bece12bc190694da7e7509cc3d303230b0a6cd0',
    ],
    packages=find_packages(),
    include_package_data=True,
)
