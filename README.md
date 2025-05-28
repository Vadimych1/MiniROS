# MiniROS
**Small and powerful robot assembling tool based on ROS principles powered by Python**

#### Work demo in tutorials folder.
<hr>

# How to install:
1. Run `scripts/install.sh` on Linux and `scripts/install.bat` on Windows.
2. Add cloned directory to PATH env variable.
3. Ready to use. Try running `miniros -h` for help. 
<hr>

# Docs
## Built-in packages:
1. turtlesim - turtle-based package that creates intefraces for controlling turtle.
2. turtlecontrol - package for controlling turtlesim
3. rgt - package for viewing MiniROS connections structure as graph.

## How to create your own package:
1. Create a new directory and CD to it. You can name it as you want, but it will be nice to use only `a-z, A-Z, 0-9, -, _`.
2. Run command `miniros create <package_name>`. You can specify some metadata for package when creating (see `miniros create -h`) or edit it in `package.xml` file.
3. Your codebase now in selected directory. Project structure:
```
/- <package_name>
/#/- build - project build
/#/- src - source files
/#/#/- source - source files
/#/#/#/- __init__.py - don`t touch it
/#/#/#/- datatypes.py - specify you datatypes here
/#/#/- __init__.py - add import * from .source.<file>
/#/#/- main.py - code that runs when calling 'miniros run package'
/#/- package.xml
```
Write your code in `src/source` folder, use it in `src/main.py`

## How to install package:
CD to project root and run `miniros install`. Run with sudo or start with admin rules of needed.

## How to run package:
Run `miniros run <package_name>`. Now you can run only installed packages. Not installed packages (source code) can be run with Python.

### See more at [docs](/docs)