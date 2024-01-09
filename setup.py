from setuptools import setup, find_packages

setup(
    name='pysoot',
    version='7.7.12.1',
    description='Get Shimple/Jimple IR in Python',
    packages=find_packages(),
    install_requires=['psutil', 'jpype1'],
)

