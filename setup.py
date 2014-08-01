from setuptools import setup, find_packages


setup(

    name='django-oscar-adyen',
    version='0.1',
    url='https://github.com/oscaro/django-oscar-adyen',
    author='Mathieu Richardoz',
    author_email='mr@babik.fr',
    description='Adyen payment module for django-oscar',
    long_description=open('README.rst').read(),
    keywords='payment, django, oscar, adyen',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'bleach==1.4',
        'django-oscar>=0.4',
        'requests>=2.0,<3.0',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Office/Business :: Financial :: Point-Of-Sale',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]

)
