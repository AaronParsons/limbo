from setuptools import setup, Extension
import os, glob, numpy, sys 

sys.path.append('limbo')

def package_files(package_dir, subdirectory):
    # walk the input package_dir/subdirectory
    # return a package_data list
    paths = []
    directory = os.path.join(package_dir, subdirectory)
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            path = path.replace(package_dir + '/', '') 
            paths.append(os.path.join(path, filename))
    return paths

data_files = package_files('limbo', 'data')

setup(name='limbo',
    version = '0.0.1',
    description = 'Software for the LIMBO project',
    long_description = 'Software for the LIMBO project',
    license = 'GPL',
    author = 'Aaron Parsons',
    author_email = 'aparsons@berkeley.edu',
    url = 'http://github.com/AaronParsons/limbo',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Topic :: Scientific/Engineering :: Astronomy',
    ],

    install_requires = [
        'astropy',
        'numpy',
        'scipy',
        'cython',
        'redis'
    ],

    ext_modules = [
        Extension(name='limbo._fdmt', sources=['limbo/_fdmt.pyx'], 
                  include_dirs=[numpy.get_include()]),
    ],

    package_dir = {'limbo':'limbo'},
    packages = ['limbo'],
    scripts = glob.glob('scripts/*'),
    package_data = {'limbo': data_files},

    include_package_data = True,
)

