# MiniROS
**Simple ROS-like tool powered by Python**

## Installation
Run these commands in your terminal to install MiniROS:
- **with venv (recommended)**:
```bash
python -m venv venv
git clone https://github.com/Vadimych1/MiniROS
venv/bin/pip install ./MiniROS # or venv/Scripts/pip on Windows
```
Do not forget to activate your venv before using MiniROS

- **without venv**:
```bash
git clone https://github.com/Vadimych1/MiniROS
cd MiniROS
pip install .
cd ..
```

## How to create and install package
1. Create a new directory and `cd` to it; use only Latin letters, numbers, dashes, and underscores
2. Run `miniros create <package_name>`. You can specify package metadata (see `miniros create -h`) or edit it directly after creation (see `package.xml`)
3. Your package is created in current directory

Project structure:
```
/- <package_name>
/#/- build - build files
/#/- src - source files
/#/#/- source - source files
/#/#/#/- datatypes.py - write your datatypes here
/#/#/- main.py - default entrypoint
/#/- package.xml - project metadata
```

MiniROS will write example code into `main.py` for you
You can change package name, version, entrypoint and other things by editing `package.xml`

## How to install package:
Run `miniros install path/to/package_root` or just `miniros install` if running in package directory

## How to run package:
Run `miniros run <package_name>`

**See how does MiniROS work at [docs](docs/Overview.md)**
