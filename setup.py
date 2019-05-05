from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    README = readme_file.read()

setup(
    name='hammer',
    version='0.1',
    packages=find_packages('.'),
    install_requires=[
        'requests',
        'web3',
        'py-solc',
        'base58',
        'rlp',
        'eth_utils',
        'two1',
        'pycrypto',
        'pycryptodome'
    ],
    author='Carlos Faria',
    author_email='carlosfaria@pm.me',
    description='Hammer to break blockchains',
    license='MIT',
    long_description=README,
    python_requires='>=3.6',
    keywords='ethereum bench tps performance',
    url='https://gitlab.com/public-mint/hammer',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
    ]
)
