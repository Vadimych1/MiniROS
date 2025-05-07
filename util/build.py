import shutil, subprocess, os

if os.path.exists("build"):
    shutil.rmtree("build")

shutil.copytree("util", "build/miniros/util")
shutil.copytree("base", "build/miniros/base")
shutil.copy2("main.py", "build/miniros/__main__.py")
with open("build/setup.py", "w") as f:
    f.write("""
from setuptools import setup

setup(
    name='miniros',
    version='0.0.1a',
    description='Main miniros package',
    license='MIT',
    packages=['miniros', 'miniros.base', 'miniros.util'],
    keywords=['package-system'],
)
""")
with open("build/miniros/__init__.py", "w") as f:
    f.write("""
from miniros.base.client import Topic, ROSClient
import miniros.util.decorators as decorators
import miniros.util.datatypes as datatypes
            
PACKAGE_NAME = "miniros"
""")

open("build/miniros/util/__init__.py", "w").close()
open("build/miniros/base/__init__.py", "w").close()

os.chdir("build")
subprocess.run(f"python3 setup.py sdist")
subprocess.run(f"python3 -m pip install dist/{os.listdir("dist")[0]} --force")
