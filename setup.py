from setuptools import setup, find_packages

setup(
    name="kentscript",
    version="3.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points={
        'console_scripts': [
            'kentscript=main:main',
        ],
    },
    package_data={
        '': ['*.ks', '*.h', '*.c', '*.asm'],
    },
    python_requires='>=3.10',
)
