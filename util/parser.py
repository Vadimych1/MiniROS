import re

class ParsingException(Exception): ...

def _connect(match, namespace):
    n = f"i{namespace["last_import_idx"]}"
    namespace["imports"][match[1]] = n
    namespace["last_import_idx"] += 1

def _subscribe(match, namespace):
    namespace["subscribes"] += [(match[0], match[1])]
    namespace["listeners"][match[0]] = {}

def _on_message(match, namespace):
    if match[1] not in namespace["listeners"][match[0]]:
        namespace["listeners"][match[0]][match[1]] = []

    namespace["listeners"][match[0]][match[1]] += [f"{namespace["imports"][match[-2]]}.{match[-1]}"]

patterns = {
    re.compile(r"CONNECT ([a-zA-Z_][a-zA-Z0-9_]*.py) AS ([a-zA-Z]+)"): _connect,
    re.compile(r"SUBSCRIBE TO ([a-zA-Z0-9]{3}) AT ([a-zA-Z0-9]{3})"): _subscribe,
    re.compile(r"ON MESSAGE FROM ([a-zA-Z0-9]{3}) AT ([a-zA-Z0-9]{3}) RUN ([a-zA-Z][a-zA-Z0-9_]*):([a-zA-Z_][a-zA-Z_0-9]*)"): _on_message,
}

def parse_ffile(fp: str):
    namespace = {
        "last_import_idx": 0,
        "imports": {},
        "subscribes": [],
        "listeners": {}
    }

    with open(fp, 'r', -1, "utf-8") as f:
        lines = f.readlines()
        idx = 1
        for line in lines:
            if len(line.strip()) == 0:
                idx += 1
                continue

            ok = False
            for pattern, func in patterns.items():
                if (m := pattern.match(line)) is not None:
                    func(m.groups(), namespace)
                    ok = True
                    break
            
            if not ok:
                raise ParsingException(f"Invalid line ({fp}:{idx}): {line}")
            
            idx += 1

parse_ffile("test.txt")