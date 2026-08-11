from setuptools import setup, find_packages

setup(
    name='netstrip',
    version='3.3.20',
    packages=find_packages(),
    package_data={
        'netstrip': [
            'data/lists/*',
            'data/*.json',
            'core/ebpf/*',
        ],
    },
)
