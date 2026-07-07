from setuptools import setup, find_packages
setup(
    name="visor",
    version="4.7.0",
    description="Visor Command Center — Jasol Group NOC Suite",
    author="Ing. Jeisson Alberto Sarmiento",
    packages=find_packages(),
    py_modules=["main"],
    python_requires=">=3.10",
    install_requires=[\"requests\",\"psutil\",\"colorama\"],
    entry_points={\"console_scripts\": [\"visor=main:main\"]},
)
