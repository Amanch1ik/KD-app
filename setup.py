from setuptools import setup, find_packages

setup(
    name='karakol-delivery',
    version='1.0.0',
    description='Delivery service backend for Karakol',
    author='Amanbol',
    author_email='amanchikaitbekov@gmail.com',
    packages=find_packages(),
    install_requires=[
        'Django==4.2.3',
        'djangorestframework==3.14.0',
        'psycopg2-binary==2.9.6',
        'django-cors-headers==4.1.0',
        'djangorestframework-simplejwt==5.2.2',
    ],
    extras_require={
        'dev': [
            'pytest==7.3.1',
            'coverage==7.2.7',
        ],
        'prod': [
            'gunicorn==20.1.0',
            'whitenoise==6.5.0',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Programming Language :: Python :: 3.10',
    ],
    python_requires='>=3.10',
)
