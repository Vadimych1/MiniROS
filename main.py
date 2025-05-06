VERSION = "0.0.1a"

import os, platformdirs
import xml.dom.minidom as xml
from argparse import ArgumentParser
import subprocess
import shutil

parser = ArgumentParser("miniros", description="A mini but powerful self-coded version of ROS")
subparsers = parser.add_subparsers(dest="subparser_name")

parser.add_argument("-v", "--version", default=False, action="store_true", dest="version")

run_parser = subparsers.add_parser("run")
create_parser = subparsers.add_parser("create")
delete_parser = subparsers.add_parser("delete")
install_parser = subparsers.add_parser("install")

run_parser.add_argument("package", type=str)
run_parser.add_argument("args", type=list, nargs="*")

create_parser.add_argument("name", type=str)
create_parser.add_argument("--maintainer", type=str, default="todo")
create_parser.add_argument("--description", type=str, default="todo")
create_parser.add_argument("--authors", type=list, nargs="+")
create_parser.add_argument("--requires", type=list, nargs="+")
create_parser.add_argument("--entrypoint", type=str, default="main.py")

delete_parser.add_argument("name", type=str)

parsed = parser.parse_args()


if parsed.version:
    print()
    print(f"MiniROS {VERSION}")
    print()
    print(r"    __  ____       _ ____            ")
    print(r"   /  |/  /_____  / / __ \____  _____")
    print(r"  / /|_/ / / __ \/ / /_/ / __ \/ ___/")
    print(r" / /  / / / / / / / _, _/ /_/ (__  ) ")
    print(r"/_/  /_/_/_/ /_/_/_/ |_|\____/____/  ")                                    
    print()
    print(f"by Vadimych1 (https://github.com/Vadimych1)")
    print()
    quit(0)


def get_package_dir(package):
    return os.path.join(platformdirs.site_data_dir(".miniros", "Vadimych1"), package)


def ask(prompt: str, choices=[], default=None):
    format_s = f"{prompt} {"/".join(choices)} {f"(default: {default})" if default is not None else ""} > "
    i = input(format_s)
    while (len(i) == 0 and default is None) or i not in choices:
        i = input(f"{prompt} {"/".join(choices)} >")
    return i if len(i) > 0 else default

match parsed.subparser_name:
    case "run":
        pkg = parsed.package
        path = get_package_dir(pkg)

        if not os.path.exists(path):
            parser.error(f"Package '{pkg}' is not exists")
            quit(1)

        doc = xml.parse(os.path.join(path, "package.xml"))

        pkg_name = doc.getElementsByTagName("name")[0].childNodes[0].nodeValue

        if pkg != pkg_name:
            parser.error(f"Package '{pkg}' has invalid XML implementation")
            quit(1)

        entrypoint = doc.getElementsByTagName("entrypoint")[0].childNodes[0].nodeValue

        print(f"\n> Running package '{pkg}' with entrypoint {entrypoint}\n")

        subprocess.run(f"python3 \"{os.path.join(path, "src", entrypoint)}\" {" ".join(parsed.args)}")

        quit(0)

    case "create":
        pkg = parsed.name
        maintainer = parsed.maintainer
        description = parsed.description
        authors = parsed.authors
        requires = parsed.requires
        entrypoint = parsed.entrypoint

        folders = [
            "src",
            "src/datatypes",
            "src/scripts",
            "build",
        ]
        files= [
            "src/main.py",
        ]

        if os.path.exists("package.xml"):
            parser.error(f"package '{pkg}' already exists in CWD")
            quit(1)

        for fld in folders:
            if os.path.exists(fld):
                print(f"Folder '{fld}', required for creating new package, already exists")
                r = ask("Overwrite it (ALL files will be lost)?", "yns", "n")
                match r:
                    case "y":
                        shutil.rmtree(fld)
                        os.mkdir(fld)
                    case "s":
                        pass
                    case "n":
                        quit(1)

        for file in files:
            if not os.path.exists(file):
                open(file, "w").close()

        doc = xml.Document()
        root = xml.Element("package")
        root.ownerDocument = doc
        doc.appendChild(root)
        
        name_e = xml.Element("name")
        name_e.ownerDocument = doc
        name_text = xml.Text()
        name_text.replaceWholeText(pkg)
        name_e.appendChild(name_text)
        root.appendChild(name_e)

        entrypoint_e = xml.Element("entrypoint")
        entrypoint_e.ownerDocument = doc
        entrypoint_text = xml.Text()
        entrypoint_text.replaceWholeText(entrypoint)
        entrypoint_e.appendChild(entrypoint_text)
        root.appendChild(entrypoint_e)

        requires_e = xml.Element("requires")
        requires_e.ownerDocument = doc
        for req in (requires if requires is not None else []):
            requirement_e = xml.Element("requirement")
            requirement_e.ownerDocument = doc
            requirement_text = xml.Text()
            requirement_text.replaceWholeText("".join(req))
            requirement_e.appendChild(requirement_text)
            requires_e.appendChild(requirement_e)
        root.appendChild(requires_e)

        maintainer_e = xml.Element("maintainer")
        maintainer_e.ownerDocument = doc
        maintainer_text = xml.Text()
        maintainer_text.replaceWholeText(maintainer)
        maintainer_e.appendChild(maintainer_text)
        root.appendChild(maintainer_e)
        
        description_e = xml.Element("description")
        description_e.ownerDocument = doc
        description_text = xml.Text()
        description_text.replaceWholeText(description)
        description_e.appendChild(description_text)
        root.appendChild(description_e)
        
        authors_e = xml.Element("authors")
        authors_e.ownerDocument = doc
        for author in (authors if authors is not None else []):
            author_e = xml.Element("author")
            author_e.ownerDocument = doc
            author_text = xml.Text()
            author_text.replaceWholeText("".join(author))
            author_e.appendChild(author_text)
            authors_e.appendChild(author_e)
        root.appendChild(authors_e)

        with open("package.xml", "w") as f:
            f.write(doc.toprettyxml())

        print(f"Successfully created new package '{pkg}'")

        quit(0)

    case "delete":
        name = parsed.name
        
        try:
            shutil.rmtree(get_package_dir(name))
        except:
            pass

        os.system(f"python3 -m pip uninstall miniros-{name}")

        quit(0)

    case "install":
        if not os.path.exists("package.xml"):
            parser.error("there is no package in CWD")

        doc = xml.parse("package.xml").getElementsByTagName("package")[0]
        name = doc.getElementsByTagName("name")[0].childNodes[0].nodeValue
        pkg_dir = get_package_dir(name)

        if not os.path.exists(pkg_dir):
            os.makedirs(pkg_dir)

        # build
        shutil.rmtree("build")
        shutil.copytree("src", f"build/miniros-{name}")
        
        if not os.path.exists("build/__init__.py"):
            open("build/__init__.py", "w").close()

        with open("build/setup.py", "w") as f:
            f.write(f"""from setuptools import setup

setup(
    name='miniros-{name}',
    version='{VERSION}',
    description='miniros package',
    license='MIT',
    packages=['{name}'],
    keywords=['example'],
)
""")

        # install to miniros run
        shutil.rmtree(os.path.join(pkg_dir, "src"))
        shutil.copy2("package.xml", os.path.join(pkg_dir, "package.xml"))
        shutil.copytree("src", os.path.join(pkg_dir, "src"))

        print("Compiling and installing package with pip")

        os.chdir("build")
        subprocess.run(f"python3 setup.py sdist")
        subprocess.run(f"python3 -m pip install dist/{os.listdir("dist")[0]} --force")

        print(f"Successfully installed package '{name}'")

        quit(0)

parser.print_help()