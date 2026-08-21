from setuptools import setup, find_packages

setup(
    name='netstrip',
    version='3.7.0',
    packages=find_packages(),
    install_requires=[
        'customtkinter>=5.2.2',
        'psutil>=5.9.8',
        'Pillow>=10.2.0',
        'plyer>=2.1.0',
        'dnslib>=0.9.24',
        'maxminddb>=2.5.2',
        'cryptography>=41.0.0',
        'requests>=2.31.0',
        'zeroconf',
        'Flask',
        'icoextract>=0.1.4',
    ],
    package_data={
        'netstrip': [
            'data/lists/*',
            'data/*.json',
            'core/ebpf/*',
        ],
    },
)
