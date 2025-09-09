VERSION = "1.1.0a"

import os, platformdirs, platform, subprocess
import xml.dom.minidom as xml
from argparse import ArgumentParser
import shutil

parser = ArgumentParser("miniros", description="Small but powerful version of ROS")
subparsers = parser.add_subparsers(dest="subparser_name")

parser.add_argument(
    "-v", "--version", default=False, action="store_true", dest="version"
)
parser.add_argument(
    "--python-executable",
    default="python" if platform.system() == "Windows" else "python3",
    dest="pyexec",
)
parser.add_argument(
    "--use-venv",
    type=str,
    dest="venv",
    default=None,
    help="specify path to venv folder",
)
parser.add_argument("--trace", action="store_true")

run_parser = subparsers.add_parser("run")
create_parser = subparsers.add_parser("create")
delete_parser = subparsers.add_parser("delete")
install_parser = subparsers.add_parser("install")
server_parser = subparsers.add_parser("server")

run_parser.add_argument("package", type=str)
run_parser.add_argument("--no-stdout", action="store_true")
run_parser.add_argument("--no-stderr", action="store_true")
run_parser.add_argument("args", type=list, nargs="*")

create_parser.add_argument("name", type=str)
create_parser.add_argument("--maintainer", type=str, default="todo")
create_parser.add_argument("--description", type=str, default="todo")
create_parser.add_argument("--authors", type=list, nargs="+")
create_parser.add_argument("--requires", type=list, nargs="+")
create_parser.add_argument("--entrypoint", type=str, default="main.py")
create_parser.add_argument("--pypackages", type=list, nargs="+", help="Python packages")

delete_parser.add_argument("name", type=str)

server_parser.add_argument("--host", type=str, default="127.0.0.1")
server_parser.add_argument("--port", type=int, default=3000)
server_parser.add_argument(
    "--superserver", type=str, default="", help="absolute path to superserver config"
)

install_parser.add_argument(
    "--no-default-readme",
    action="store_true",
    help="disable README.md autogeneration if it`s not found",
)

parsed = parser.parse_args()

PYTHON_EXEC = parsed.pyexec

if parsed.version:
    print()
    print(f"MiniROS {VERSION}")
    print()
    print(r"\033[1;36m    __  ____       _ ____            ")
    print(r"\033[1;36m   /  |/  /_____  / / __ \____  _____")
    print(r"\033[1;36m  / /|_/ / / __ \/ / /_/ / __ \/ ___/")
    print(r"\033[1;36m / /  / / / / / / / _, _/ /_/ (__  ) ")
    print(r"\033[1;36m/_/  /_/_/_/ /_/_/_/ |_|\____/____/  ")
    print()
    print("\033[0;36mby Vadimych1 (https://github.com/Vadimych1)\033[0m")
    print()
    quit(0)

if parsed.venv is not None:
    PYTHON_EXEC = os.path.join(parsed.venv, "/Scrips/python3")


def get_package_dir(package):
    if platform.system() == "Windows":
        return os.path.join(
            platformdirs.site_data_dir(".miniros", "Vadimych1"), package
        )

    else:
        return os.path.join("/var", "lib", ".miniros", package)


def ask(prompt: str, choices=[], default=None):
    format_s = f"{prompt} {'/'.join(choices)} {f'(default: {default})' if default is not None else ''} > "
    i = input(format_s)
    while (len(i) == 0 and default is None) or i not in choices:
        i = input(f"{prompt} {'/'.join(choices)} >")
    return i if len(i) > 0 else default


def trace(*args):
    if parsed.trace:
        print("[TRACE]", *args)


trace("py executable", PYTHON_EXEC)
trace("command", parsed.subparser_name)

match parsed.subparser_name:
    case "run":
        pkg = parsed.package
        path = get_package_dir(pkg)

        trace(pkg, path)

        if not os.path.exists(path):
            parser.error(f"package '{pkg}' does not exist")
            quit(1)

        doc = xml.parse(os.path.join(path, "package.xml"))

        pkg_name = doc.getElementsByTagName("name")[0].childNodes[0].nodeValue

        if pkg != pkg_name:
            parser.error(f"package '{pkg}' has invalid XML implementation")
            quit(1)

        entrypoint = doc.getElementsByTagName("entrypoint")[0].childNodes[0].nodeValue

        print(
            f"\033[1;32m[MiniROS] Running package '{pkg}' with entrypoint {entrypoint}\033[0m\n"
        )

        try:
            proc = subprocess.run(
                [
                    PYTHON_EXEC,
                    os.path.join(path, "src", entrypoint),
                    *list(map("".join, parsed.args))
                ],
                check=True,
                stdout=subprocess.DEVNULL if parsed.no_stdout else None,
                stderr=subprocess.DEVNULL if parsed.no_stderr else None,
            )

        except Exception as e:
            print(f"\n\033[1;31m[MiniROS] Package '{pkg}' exited with error\033[0m")
            quit(1)

        print(f"\n\033[1;32m[MiniROS] Package '{pkg}' exited successfully\033[0m")
        quit(0)

    case "create":
        pkg = parsed.name
        pkg = pkg.replace("-", "_").replace(" ", "_")
        maintainer = parsed.maintainer
        description = parsed.description
        authors = parsed.authors
        requires = parsed.requires
        entrypoint = parsed.entrypoint
        otherexts = parsed.pypackages

        trace(pkg, maintainer, description, authors, requires, entrypoint)

        folders = [
            "src",
            "src/source",
            "build",
        ]
        files = [
            "src/main.py",
            "src/source/datatypes.py",
            "src/source/__init__.py",
            "src/__init__.py",
        ]

        if os.path.exists("package.xml"):
            parser.error(f"package '{pkg}' already exists in CWD")
            quit(1)

        for fld in folders:
            if os.path.exists(fld):
                print(
                    f"Folder '{fld}', required for creating new package, already exists"
                )
                r = ask("Overwrite it (ALL files will be lost)?", "yns", "n")
                match r:
                    case "y":
                        shutil.rmtree(fld)
                        os.mkdir(fld)
                    case "s":
                        pass
                    case "n":
                        quit(1)

            else:
                os.mkdir(fld)

        for file in files:
            if not os.path.exists(file):
                open(file, "w").close()

        with open("src/__init__.py", "w") as f:
            f.write(
                """
# Add your importables here
from source.datatypes import *
"""
            )

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
        for req in requires if requires is not None else []:
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
        for author in authors if authors is not None else []:
            author_e = xml.Element("author")
            author_e.ownerDocument = doc
            author_text = xml.Text()
            author_text.replaceWholeText("".join(author))
            author_e.appendChild(author_text)
            authors_e.appendChild(author_e)
        root.appendChild(authors_e)

        otherexts_e = xml.Element("python-packages")
        otherexts_e.ownerDocument = doc
        for ext in otherexts if otherexts is not None else []:
            ext_e = xml.Element("pp")
            ext_e.ownerDocument = doc
            ext_text = xml.Text()
            ext_text.replaceWholeText("".join(ext))
            ext_e.appendChild(ext_text)
            otherexts_e.appendChild(ext_e)
        root.appendChild(otherexts_e)

        linux_scripts_e = xml.Element("linux-scripts")
        linux_scripts_e.ownerDocument = doc

        linux_script_e = xml.Element("lscript")
        linux_scripts_e.ownerDocument = doc
        linux_script_text = xml.Text()
        linux_script_text.replaceWholeText("echo Done!")

        linux_scripts_e.appendChild(linux_script_e)
        root.appendChild(linux_scripts_e)

        windows_scripts_e = xml.Element("windows-scripts")
        windows_scripts_e.ownerDocument = doc

        windows_script_e = xml.Element("wscript")
        windows_scripts_e.ownerDocument = doc
        windows_script_text = xml.Text()
        windows_script_text.replaceWholeText("echo Done!")

        windows_scripts_e.appendChild(windows_script_e)
        root.appendChild(windows_scripts_e)

        with open("package.xml", "w") as f:
            f.write(doc.toprettyxml())

        print(f"\033[1;32m[MiniROS] Successfully created new package '{pkg}'\033[0m")

        quit(0)

    case "delete":
        name = parsed.name
        trace(name)

        try:
            shutil.rmtree(get_package_dir(name.replace("-", "_").replace(" ", "_")))
        except:
            pass

        subprocess.run(
            [
                PYTHON_EXEC,
                "-m",
                "pip",
                "uninstall",
                f"miniros_{name.replace('-', '_').replace(' ', '_')}",
            ]
        )

        quit(0)

    case "install":
        if not os.path.exists("package.xml"):
            parser.error("there is no package in current directory")

        doc = xml.parse("package.xml").getElementsByTagName("package")[0]
        name = doc.getElementsByTagName("name")[0].childNodes[0].nodeValue
        pname = name.replace("-", "_").replace(" ", "_")
        pkg_dir = get_package_dir(pname)

        otherexts = map(
            lambda x: x.childNodes[0].nodeValue, doc.getElementsByTagName("pp")
        )

        trace(name, pkg_dir)

        if not os.path.exists(pkg_dir):
            os.makedirs(pkg_dir)

        # build
        if os.path.exists("build"):
            shutil.rmtree("build")

        shutil.copytree("src", f"build/miniros_{pname}")

        if not os.path.exists("build/__init__.py"):
            open("build/__init__.py", "w").close()

        with open("build/setup.py", "w") as f:
            f.write(
                f"""from setuptools import setup

setup(
    name='miniros_{pname}',
    version='{VERSION}',
    description='miniros package',
    license='MIT',
    packages=['miniros_{pname}', 'miniros_{pname}.source'],
    keywords=[],
)
"""
            )

        try:
            found = False
            for x in os.listdir():
                if "readme" in x.lower() and os.path.isfile(x):
                    shutil.copy2(x, f"build/{x}")
                    found = True
                    break
            if not found:
                raise Exception("-")

        except Exception as e:
            if not parsed.no_default_readme:
                print("\033[1;31mREADME file is not found (created default)\033[0m")

                with open("build/README.md", "w") as f:
                    f.write(f"# Package {pname}")

        # copy to packages folder for 'miniros run'
        shutil.rmtree(pkg_dir)
        os.makedirs(pkg_dir)
        shutil.copy2("package.xml", os.path.join(pkg_dir, "package.xml"))
        shutil.copytree("src", os.path.join(pkg_dir, "src"))

        print("\033[0;34m[MiniROS] Compiling and installing package with pip")

        os.chdir("build")

        subprocess.run([PYTHON_EXEC, "./setup.py", "sdist"], stdout=subprocess.DEVNULL)
        subprocess.run(
            [
                PYTHON_EXEC,
                "-m",
                "pip",
                "install",
                f"dist/{os.listdir('dist')[0]}",
                "--force",
                "--break-system-packages",
            ],
            stdout=subprocess.DEVNULL,
        )
        os.chdir("../../")

        print("\033[0;34m[MiniROS] Installing specified python packages")
        for x in otherexts:
            try:
                subprocess.run([PYTHON_EXEC, "-m", "pip", "install", x])
            except Exception as e:
                print(f"\033[1;31mFailed to install Python package {x}:", e, "\033[0m")

        print("\033[0;34m[MiniROS] Running platform-specific scripts")

        sys = platform.system()

        def _get_val(x):
            try:
                return x.childNodes[0].nodeValue
            except:
                return ""

        if sys == "Windows":
            scripts = map(_get_val, doc.getElementsByTagName("wscript"))

        elif sys == "Linux":
            scripts = map(_get_val, doc.getElementsByTagName("lscript"))

        else:  # TODO
            scripts = []

        for x in scripts:
            os.system(x)

        print(f"\033[1;32m[MiniROS] Successfully installed package '{pname}'\033[0m\n\n")

        quit(0)

    case "server":
        from miniros.base.server import run
        import asyncio

        host, port = parsed.host, parsed.port

        trace(host, port)

        print(f"\033[1m[MiniROS] Running at {host}:{port}\033[0m")

        if len(parsed.superserver.strip()) > 0:
            from miniros import AsyncROSClient
            from miniros.base.server import AsyncDistributedServer
            import json

            trace(parsed.superserver)
            with open(parsed.superserver, "r") as f:
                cfg = json.load(f)

                lip, lport = cfg["local_ip"], cfg["local_port"]
                rip, rport = cfg["remote_ip"], cfg["remote_port"]

                name = cfg["robot_name"]

                class OnRobotClient(AsyncROSClient): ...

                class OnServerClient(AsyncROSClient): ...

                robot_client = OnRobotClient(
                    "l_" + name, _parse_handlers=False, ip=lip, port=lport
                )
                server_client = OnServerClient(
                    "r_" + name, _parse_handlers=False, ip=rip, port=rport
                )

                for forwarder in cfg["on_server"]:

                    def h():
                        _forwarder = forwarder.copy()

                        async def _forward(data):
                            await server_client.wait(False)
                            await server_client.anon(
                                _forwarder["to_node"],
                                _forwarder["to_field"],
                                data,
                                # force_to_tcp=True, # TODO: fix udp
                            )

                        robot_client.fields.append(
                            (
                                _forwarder["from_node"],
                                _forwarder["from_field"],
                                _forward,
                            )
                        )

                    h()

                for forwarder in cfg["on_robot"]:

                    def h():
                        _forwarder = forwarder.copy()

                        async def _forward(data):
                            await robot_client.wait(False)
                            await robot_client.anon(
                                _forwarder["to_node"],
                                _forwarder["to_field"],
                                data,
                                # force_to_tcp=True, # TODO: fix udp
                            )

                        server_client.fields.append(
                            (
                                _forwarder["from_node"],
                                _forwarder["from_field"],
                                _forward,
                            )
                        )

                    h()

                s = AsyncDistributedServer(host, port)

                async def run_srv_client():
                    await s.wait()
                    await asyncio.gather(server_client.run(), server_client.wait())

                async def run_rbt_client():
                    await s.wait()
                    await asyncio.gather(robot_client.run(), robot_client.wait())

                async def main():
                    await asyncio.gather(
                        s.run(),
                        run_srv_client(),
                        run_rbt_client(),
                    )

                asyncio.run(main())

        else:
            asyncio.run(run(host, port))

        quit(0)

parser.print_help()
