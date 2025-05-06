import shutil, subprocess, os

if os.path.exists("build"):
    shutil.rmtree("build")

shutil.copytree("util", "build/miniros/base")
shutil.copytree("base", "build/miniros/util")
shutil.copy2("main.py", "build/miniros/__main__.py")
with open("build/setup.py", "w") as f:
    f.write("""
from setuptools import setup

setup(
    name='miniros',
    version='0.0.1a',
    description='Main miniros package',
    license='MIT',
    packages=['miniros'],
    keywords=['package-system'],
)
""")

os.chdir("build")
subprocess.run(f"python3 setup.py sdist")
subprocess.run(f"python3 -m pip install dist/{os.listdir("dist")[0]} --force")
