"""
setup.py — Instala Visor como comando de sistema.

Uso:
    pip install -e .        → instala en modo editable (recomendado para desarrollo)
    pip install .           → instala en el sistema
    pip uninstall visor     → desinstala

Después de instalar, puedes ejecutar simplemente:
    visor
    visor --scan
    visor --web
    visor --internet
    visor --setup
    visor --report
"""

from setuptools import setup, find_packages

setup(
    name="visor",
    version="2.0.0",
    description="Monitor de Red ligero para NOC/ISP — by Jasol Group",
    author="Jasol Group",
    author_email="jasol@example.com",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "visor=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
