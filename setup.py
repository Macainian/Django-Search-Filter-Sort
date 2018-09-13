from setuptools import setup, find_packages

setup(
    name='django-search-filter-sort',
    version='0.1.13',
    # find_packages() takes a source directory and two lists of package name patterns to exclude and include.
    # If omitted, the source directory defaults to the same directory as the setup script.
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/Macainian/Django-Search-Filter-Sort',
    license='MIT License',
    author='Keith Hostetler',
    author_email='robh@syscon-intl.com',
    description='Django app designed to help with the creation of list views with full functionality for searching, '
                'filtering, and sorting.',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)