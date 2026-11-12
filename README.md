# MiniROS
**Simple ROS-like communication system powered by Python**

## Installation
MiniROS requires python>=3.10
```bash
python -m venv venv
source venv/bin/activate
git clone https://github.com/Vadimych1/MiniROS
pip install ./MiniROS # or venv/Scripts/pip on Windows
```

## Creating package
Package creation is simple:
1. make a new directory and `cd` there;
2. run `miniros create <package_name> [args]`

Type `miniros create -h` to see what arguments does package creation support

This will create a basic MiniROS package with default file contents, including `package.xml` and `main.py`

## How to install package:
Installing package:
1. from specified directory: `miniros install <path/to/package>`
2. from current directory: `miniros install`

When installing, MiniROS will copy project files into `build` dir, add Python-package related files, then compile and install wheel

You can replace MiniROS default `pyproject.toml` generation by putting it into the package root

You can also put your `README.md` here, it will be included into the Python package installation 

## How to run package:
Type `miniros run <package_name>`. This will run entrypoint (default `main.py`) of specified package

**See more about MiniROS at [docs](docs/Overview.md)**
