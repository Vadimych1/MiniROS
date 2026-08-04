from argparse import ArgumentParser
import platform, platformdirs
import os


def ask(prompt: str, choices=None, default=None):
    if choices is None:
        choices = []

    format_s = f"{prompt} {'/'.join(choices)} {f'(default: {default})' if default is not None else ''} > "

    while True:
        i = input(format_s)

        if not i and default is not None:
            return default

        if i in choices:
            return i


# TODO: test platformdirs solution on linux and use it
def get_package_dir(package):
    # if platform.system() == "Windows":
    return os.path.join(
        platformdirs.user_data_dir("miniros", "Vadimych1"), package
    )
    # else:
    #     return os.path.join("/var", "lib", ".miniros", package)


def parse_arguments():
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
    create_parser.add_argument(
        "--pypackages", type=list, nargs="+", help="Python packages"
    )

    delete_parser.add_argument("name", type=str)

    server_parser.add_argument("--host", type=str, default="127.0.0.1")
    server_parser.add_argument("--port", type=int, default=3000)
    server_parser.add_argument(
        "--superserver",
        type=str,
        default="",
        help="absolute path to superserver config",
    )

    install_parser.add_argument(
        "--no-default-readme",
        action="store_true",
        help="disable README.md autogeneration if it`s not found",
    )

    parsed = parser.parse_args()

    return parser, parsed
