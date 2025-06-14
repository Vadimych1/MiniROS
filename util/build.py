import shutil, subprocess, os, argparse

parser = argparse.ArgumentParser()
parser.add_argument("--version", "-v", type=str, required=True)
pd = parser.parse_args()

VERSION = pd.version

if os.path.exists("build"):
    shutil.rmtree("build")

shutil.copytree("util", "build/miniros/util")
shutil.copytree("base", "build/miniros/base")
shutil.copy2("main.py", "build/miniros/__main__.py")
with open("build/setup.py", "w") as f:
    f.write(f"""
from setuptools import setup

setup(
    name='miniros',
    version='{VERSION}',
    description='Main miniros package',
    license='MIT',
    packages=['miniros', 'miniros.base', 'miniros.util'],
    keywords=['package-system'],
)
""")
with open("build/miniros/__init__.py", "w") as f:
    f.write(f"""
from miniros.base.client import Topic, AsyncTopic, ROSClient, AsyncROSClient
from miniros.util.decorators import decorators
import miniros.util.datatypes as datatypes
import miniros.util.util as utils
            
PACKAGE_NAME = "miniros"
__version__ = "{VERSION}"
""")

open("build/miniros/util/__init__.py", "w").close()
open("build/miniros/base/__init__.py", "w").close()

os.chdir("build")

try: shutil.rmtree("./dist", True) # remove prev dists
except: pass

r = subprocess.run(f"python3 setup.py sdist")
r.check_returncode()

r = subprocess.run(f"python3 -m pip install dist/{os.listdir("dist")[0]} --force")
r.check_returncode()