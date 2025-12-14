import shutil, os, argparse, glob, platform, subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--version", "-v", type=str, default="1.0.2b0")
parser.add_argument("--pyexec", "-e", type=str, default="python3")
parser.add_argument("--use-sh", action="store_true")
pd = parser.parse_args()

VERSION = pd.version

print("\033[1;34mRunning build\033[0m")
print("\033[1;34mCopying files\033[0m")

try:
    if os.path.exists("build"):
        shutil.rmtree("build")
except:
    pass

shutil.copytree("util", "build/miniros/util")
shutil.copytree("base", "build/miniros/base")
shutil.copytree("simulator", "build/miniros/simulator")
shutil.copy2("main.py", "build/miniros/__main__.py")
with open("build/setup.py", "w") as f:
    f.write(f"""
from setuptools import setup

setup(
    name='miniros',
    version='{VERSION}',
    description='Main miniros package',
    license='MIT',
    packages=['miniros', 'miniros.base', 'miniros.util', 'miniros.simulator'],
    keywords=['package-system','robotics','ros'],
)
""")
# TODO: remove decorators.decorators import
with open("build/miniros/__init__.py", "w") as f:
    f.write(f"""
from miniros.base.client import Topic, AsyncTopic, ROSClient, AsyncROSClient
from miniros.util.decorators import decorators, parsedata, aparsedata, threaded
import miniros.util.datatypes as datatypes
import miniros.util.util as utils
            
PACKAGE_NAME = "miniros"
__version__ = "{VERSION}"
""")

open("build/miniros/util/__init__.py", "w").close()
open("build/miniros/base/__init__.py", "w").close()
open("build/miniros/simulator/__init__.py", "w").close()
shutil.copy2("README.md", "build/README.md")

print("\033[1;34mInstalling requriements...\033[0m")
subprocess.run([pd.pyexec, "-m", "pip", "install", "-r", "requirements.txt"])

os.chdir("build")

print("\033[1;34mRemoving previous dist\033[0m")
try: shutil.rmtree("./dist", True)
except: pass

print("\033[1;34mBuilding package...\033[0m")
subprocess.run([pd.pyexec, "-m", "build", "--wheel"], stdout=subprocess.DEVNULL)

print("\033[1;34mInstalling\033[0m")
subprocess.run([pd.pyexec, "-m", "pip", "install", f"dist/{os.listdir('dist')[0]}", "--force", "--break-system-packages"], stdout=subprocess.DEVNULL)

# run install scripts
os.chdir("../scripts/on_install")

print("\033[1;34mRunning platform-specific scripts...\033[0m")
match platform.system():
    case "Windows":
        for cmd in glob.glob("./*.bat"):
            os.system(cmd)
    
    case "Linux":
        for cmd in glob.glob("./*.sh"):
            os.system(f"{'sh' if pd.use_sh else 'bash'} {cmd}")
            
print("\n\033[1;32mDone!\033[0m\n")
