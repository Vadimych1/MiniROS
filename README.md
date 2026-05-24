# MiniROS
**Small and powerful robot assembling tool based on ROS principles powered by Python**

<!-- ## Built-in packages:
1. turtlesim - turtle-based package that creates intefraces for controlling turtle.
2. turtlecontrol - package for controlling turtlesim
3. rgt - package for viewing MiniROS connections structure as graph. -->

## How to create your own package:
1. Create a new directory and CD to it. You can name it as you want, but it will be nice to use only `a-z, A-Z, 0-9, -, _`.
2. Run command `miniros create <package_name>`. You can specify some metadata for package when creating (see `miniros create -h`) or edit it in `package.xml` file.
3. Your codebase is now in specified directory. 

Project structure:
```
/- <package_name>
/#/- build - project build
/#/- src - source files
/#/#/- source - source files
/#/#/#/- __init__.py - don`t touch it
/#/#/#/- datatypes.py - specify your datatypes here
/#/#/- __init__.py - add import * from .source.<file>
/#/#/- main.py - code that runs with 'miniros run <package>'
/#/- package.xml - metadata of the project
```
Write your code in `src/source` folder, use it in `src/main.py`

## How to install package:
CD to project root and run `miniros install`. Run with sudo or start with admin rules of needed.

## How to run package:
Run `miniros run <package_name>`. You can run only installed packages. Non-installed packages (source code) can be run via plain Python.

**See how does MiniROS work at [docs](docs/Overview.md)**
