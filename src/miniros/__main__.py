from miniros.util.src.helpers import *
import os, subprocess, sys
import xml.dom.minidom as xml
import xml.etree.ElementTree as ET
import shutil, psutil, time, signal
import importlib.resources, importlib.metadata
import re
from dataclasses import dataclass, field

try:
    VERSION = importlib.metadata.version("miniros")
    BASIC_MAIN_FILE = (
        importlib.resources.files("miniros")
        .joinpath("demo/main.example.py")
        .read_text()
    )
except Exception as e:
    print(e)

    VERSION = "[unknown]"
    BASIC_MAIN_FILE = 'print("Hello, world")'


@dataclass
class PackageInfo:
    name: str
    entrypoint: str
    maintainer: str
    description: str
    version: str
    authors: list[str] = field(default_factory=list)
    pip_requirements: list[str] = field(default_factory=list)
    miniros_requirements: list[str] = field(default_factory=list)


def error(*args):
    print(f"\033[0;31m[ERROR]", *args, "\033[0m\n")


def info(*args):
    print(f"\033[1;32m[INFO]", *args, "\033[0m")


def warn(*args):
    print(f"\033[1;33m[WARNING]", *args, "\033[0m")


def create_xml_element(doc, tag, text=None, children=None):
    element = xml.Element(tag)
    element.ownerDocument = doc
    if text is not None:
        text_node = xml.Text()
        text_node.replaceWholeText(str(text))
        element.appendChild(text_node)
    if children:
        for child in children:
            element.appendChild(child)
    return element


def parse_package_xml(xml_path: str) -> PackageInfo:
    if not os.path.exists(xml_path):
        error(f"xml file was not found in '{xml_path}'")
        sys.exit(1)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    name = root.get("name")
    version = root.get("version")

    entrypoint = root.findtext("entrypoint")
    maintainer = root.findtext("maintainer")
    description = root.findtext("description")

    authors = [
        author.text.strip() for author in root.findall("authors/author") if author.text
    ]

    pip_reqs = [
        pip.text.strip() for pip in root.findall("requirements/pip") if pip.text
    ]
    miniros_reqs = [
        miniros.text.strip()
        for miniros in root.findall("requirements/miniros")
        if miniros.text
    ]

    if None in [name, entrypoint, maintainer, description]:
        raise ValueError("invalid xml file")

    return PackageInfo(
        name,  # type: ignore
        entrypoint,  # type: ignore
        maintainer,  # type: ignore
        description,  # type: ignore
        version,  # type: ignore
        authors,
        pip_reqs,
        miniros_reqs,
    )


def write_package_xml(xml_path: str, package_info: PackageInfo) -> None:
    doc = xml.Document()
    root = create_xml_element(doc, "package")
    doc.appendChild(root)

    root.setAttribute("name", package_info.name)
    root.setAttribute("version", package_info.version)

    root.appendChild(
        create_xml_element(doc, "entrypoint", text=package_info.entrypoint)
    )
    root.appendChild(
        create_xml_element(doc, "maintainer", text=package_info.maintainer)
    )
    root.appendChild(
        create_xml_element(doc, "description", text=package_info.description)
    )
    authors_e = create_xml_element(doc, "authors")
    for author in package_info.authors:
        author_e = create_xml_element(doc, "author", text=author)
        authors_e.appendChild(author_e)
    root.appendChild(authors_e)

    requirements_e = create_xml_element(doc, "requirements")
    for pack_name in package_info.pip_requirements:
        package = create_xml_element(doc, "pip", text=pack_name)
        requirements_e.appendChild(package)

    for pack_name in package_info.miniros_requirements or []:
        package = create_xml_element(doc, "miniros", text=pack_name)
        requirements_e.appendChild(package)

    root.appendChild(requirements_e)

    with open(xml_path, "w") as f:
        f.write(doc.toprettyxml())


def prepare_name(package: str) -> str:
    if re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_-]{,30}[a-zA-Z0-9]$", package) is not None:
        return package.replace("-", "_")

    else:
        error(f"package name '{package}' is invalid")
        sys.exit(1)


def get_pip_name(package: str) -> str:
    return f"miniros_{prepare_name(package)}"


def run_main() -> None:
    parser, parsed = parse_arguments()

    def trace(*args):
        if parsed.trace:
            print("[TRACE]", *args)

    PYTHON_EXEC = sys.executable

    if parsed.version:
        print()
        print(f"MiniROS {VERSION}")
        print()
        print("\033[1;36m    __  ____       _ ____            ")
        print("\033[1;36m   /  |/  /_____  / / __ \\____  _____")
        print("\033[1;36m  / /|_/ / / __ \\/ / /_/ / __ \\/ ___/")
        print("\033[1;36m / /  / / / / / / / _, _/ /_/ (__  ) ")
        print("\033[1;36m/_/  /_/_/_/ /_/_/_/ |_|\\____/____/  ")
        print()
        print("\033[0;36mby Vadimych1 (https://github.com/Vadimych1)\033[0m")
        print()
        sys.exit(0)

    trace("py executable", PYTHON_EXEC)
    trace("command", parsed.subparser_name)

    match parsed.subparser_name:
        case "run":
            name = prepare_name(parsed.package)
            pip_name = get_pip_name(name)

            try:
                trace("package v", importlib.metadata.version(pip_name))
            except importlib.metadata.PackageNotFoundError:
                error(f"package '{name}' does not exist")
                sys.exit(1)

            package = parse_package_xml(
                str(importlib.resources.files(pip_name).joinpath("package.xml"))
            )
            pkg_name = package.name
            entrypoint = package.entrypoint

            if pkg_name != name:
                error(f"package '{name}' has invalid xml file")
                sys.exit(1)

            info(f"running package '{name}' with entrypoint", entrypoint)

            command = [PYTHON_EXEC, "-m", f"{pip_name}.{entrypoint}", *["".join(x) for x in parsed.args]]

            stdout = subprocess.DEVNULL if parsed.no_stdout else None
            stderr = subprocess.DEVNULL if parsed.no_stderr else None

            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr)
            p = psutil.Process(proc.pid)
            interrupted = False

            try:
                if parsed.log_stats is not None:
                    p.cpu_percent(interval=None)
                    time.sleep(0.1)

                    with open(parsed.log_stats, "w") as f:
                        f.write("idx\ttime\tcpu_perc\tmem_mb")
                        i = 0

                        while proc.poll() is None:
                            i += 1

                            try:
                                ctime = time.time()

                                cpu_perc = p.cpu_percent(interval=None)
                                ram_usage_mb = p.memory_info().rss / (1024 * 1024)

                                f.write(
                                    f"\n{i}\t{ctime:<.2f}\t{cpu_perc:<.2f}\t{ram_usage_mb:<.2f}"
                                )
                                f.flush()

                                time.sleep(0.5)

                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                break

                            except KeyboardInterrupt:
                                interrupted = True
                                break

                else:
                    while proc.poll() is None:
                        time.sleep(0.1)

            except KeyboardInterrupt:
                interrupted = True

            if interrupted:
                if sys.platform != "win32":
                    try:
                        proc.send_signal(signal.SIGINT)
                    except ProcessLookupError:
                        pass

                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

            info(f"package '{name}' finished")
            sys.exit(0)

        case "create":
            if not parsed.skip:
                choice = ask(
                    "Package will be created in current working directory. Continue?",
                    "yn",
                    "y",
                )
                if choice == "n":
                    sys.exit(1)

            pkg = parsed.name
            pkg = prepare_name(pkg)

            trace("pkg", pkg)
            trace("maintainer", parsed.maintainer)
            trace("description", parsed.description)
            trace("authors", parsed.authors)
            trace("entrypoint", parsed.entrypoint)
            trace("version", parsed.pack_ver)
            trace("r_pip", parsed.requires_pip)
            trace("r_miniros", parsed.requires_miniros)

            package = PackageInfo(
                pkg,
                parsed.entrypoint,
                parsed.maintainer,
                parsed.description,
                parsed.pack_ver,
                parsed.authors or [],
                parsed.requires_pip or [],
                parsed.requires_miniros or [],
            )

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
                error(f"package already exists in the current directory")
                sys.exit(1)

            for fld in folders:
                if os.path.exists(fld):
                    r = ask(
                        f"Folder '{fld}' already exists\n"
                        "Overwrite it (ALL the files will be lost)?",
                        "yns",
                        "n",
                    )
                    match r:
                        case "y":
                            shutil.rmtree(fld)
                            os.mkdir(fld)
                        case "s":
                            pass
                        case "n":
                            sys.exit(1)

                else:
                    os.mkdir(fld)

            for file in files:
                if not os.path.exists(file):
                    open(file, "w").close()

            with open("src/main.py", "w") as f:
                f.write(BASIC_MAIN_FILE)

            with open("src/__init__.py", "w") as f:
                f.write(
                    "# Add your importables here\n" "from .source.datatypes import *\n"
                )

            write_package_xml("package.xml", package)

            info(f"successfully created new package '{pkg}'")

            sys.exit(0)

        case "uninstall":
            name = prepare_name(parsed.name)

            trace(name)

            if ask(f"Do you want to delete package '{name}'", "yn", "n") == "n":
                sys.exit(0)

            subprocess.run(
                [
                    PYTHON_EXEC,
                    "-m",
                    "pip",
                    "uninstall",
                    get_pip_name(name),
                ],
                stdout=subprocess.DEVNULL,
            )

            info(f"successfully deleted package '{name}'")

            sys.exit(0)

        case "install":
            path = parsed.package_path

            if path is not None:
                if not os.path.exists(path):
                    error(f"directory '{path}' was not found")

                else:
                    os.chdir(path)

            if not os.path.exists("package.xml"):
                error("package.xml was not found")

            package = parse_package_xml("package.xml")
            name = prepare_name(package.name)
            pip_packages = package.pip_requirements

            pip_name = get_pip_name(name)

            trace("name", name)
            trace("pip_packages", pip_packages)

            # build
            if os.path.exists("build"):
                shutil.rmtree("build")

            shutil.copytree("src", f"build/{pip_name}")
            shutil.copy2("package.xml", f"build/{pip_name}/package.xml")

            if not os.path.exists("build/__init__.py"):
                open("build/__init__.py", "w").close()

            readme_name = None
            try:
                found = False
                for x in os.listdir():
                    if x.lower().startswith("readme.") and os.path.isfile(x):
                        shutil.copy2(x, f"build/{x}")
                        readme_name = x
                        found = True
                        break

                if not found:
                    raise Exception("-")

            except Exception:
                if not parsed.no_default_readme:
                    warn("README file is not found (created default)")

                    readme_name = "README.md"
                    with open("build/README.md", "w") as f:
                        f.write(f"# Package {name}")

            if not os.path.exists("pyproject.toml"):
                with open("build/pyproject.toml", "w") as f:
                    f.write(
                        "[build-system]\n"
                        'requires = ["hatchling"]\n'
                        'build-backend = "hatchling.build"\n'
                        "\n"
                        "[project]\n"
                        f'name = "{pip_name}"\n'
                        f'version = "{package.version}"\n'
                        f'description = "{package.description}"\n'
                        "authors = [\n"
                        '    {name = "todo todo", email = "mail@example.com"}\n'  # TODO: generate this
                        "]\n"
                        'requires-python = ">=3.9"\n'
                        f'readme = "{readme_name}"\n'
                        "dependencies = [\n"
                        f'   {",\n   ".join(f'"{req}"' for req in pip_packages)}'
                        "]\n"
                        "\n"
                        "[tool.hatch.build.targets.wheel]\n"
                        f'artifacts = ["{pip_name}/*.xml"]\n'
                        f'packages = ["{pip_name}/"]'
                    )

            else:
                shutil.copy2("pyproject.toml", "build/pyproject.toml")

            info("compiling and installing package with pip")

            os.chdir("build")

            subprocess.run(
                [
                    PYTHON_EXEC,
                    "-m",
                    "pip",
                    "install",
                    ".",
                    "--force",
                ],
                stdout=subprocess.DEVNULL,
            )
            os.chdir("../../")

            info(f"successfully installed package '{name}'")

            sys.exit(0)

        case "show":
            name = prepare_name(parsed.package)
            pip_name = get_pip_name(name)

            try:
                trace("package v", importlib.metadata.version(pip_name))
            except importlib.metadata.PackageNotFoundError:
                error(f"package '{name}' does not exist")
                sys.exit(1)

            package = parse_package_xml(
                str(importlib.resources.files(pip_name).joinpath("package.xml"))
            )

            info(f"Showing package {pip_name}")
            print("-" * 15)
            print(f"Name:", package.name)
            print(f"Version:", package.version)
            print(f"Maintainer:", package.maintainer)
            print(f"Authors:", ", ".join(package.authors))
            print(f"Description:", package.description)
            print(f"Entrypoint:", package.entrypoint)
            print(f"Python requirements:", ", ".join(package.pip_requirements))
            print(f"MiniROS requirements:", ", ".join(package.miniros_requirements))
            print("-" * 15)

            sys.exit(0)

        case "server":
            from miniros.base.server import run
            import asyncio

            host, port = parsed.host, parsed.port

            trace("host", host)
            trace("port", port)

            info(f"running at {host}:{port}")
            
            try:
                asyncio.run(run(host, port))

            except KeyboardInterrupt:
                info("shutting down")
                pass

            sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    run_main()
