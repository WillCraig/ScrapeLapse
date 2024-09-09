from setuptools import setup, find_packages

setup(
    name='image_timelapse',
    version='0.1.0',
    description='A project to download images and create a time-lapse video.',
    author='William Craig',
    author_email='wcraig@enbasis.com',
    url='https://github.com/willcraig/ScrapeLapse',
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4',
        'opencv-python',
        'python-dotenv'
    ],
    entry_points={
        'console_scripts': [
            'image_timelapse=main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)