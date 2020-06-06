from distutils.core import setup
from Cython.Build import cythonize

ext_modules = [
    "router.py",
    "settings.py",
    "app/db.py",
    "app/filters.py",
    "app/resources.py",
]

setup(
    ext_modules=cythonize(ext_modules)
)

# python3 setup.py build_ext --inplace
