from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='tom_astrosource',
    version='0.0.1',
    description='Astrosource pipeline for tom_education',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Joe Singleton',
    author_email='joesingo@gmail.com',
    install_requires=[
        'astrosource @ git+https://github.com/zemogle/astrosource@d02a9ae274cd88ca119f912433f078e19173abb5',
    ],
    packages=find_packages(),
    include_package_data=True,
)
