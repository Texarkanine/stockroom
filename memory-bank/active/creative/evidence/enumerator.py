import json, sys, glob, os
from collections import defaultdict

def short(v):
    s = repr(v)
    return s if len(s) <= 90 else s[:90] + "…"

class Acc:
    def __init__(self):
        # kind -> path -> {count, pytypes:set, sample}
        self.data = defaultdict(lambda: defaultdict(lambda: {"count":0,"types":set(),"sample":None}))
        self.kind_count = defaultdict(int)
    def add(self, kind, path, val):
        d = self.data[kind][path]
        d["count"] += 1
        d["types"].add(type(val).__name__)
        if d["sample"] is None and val not in (None, "", [], {}):
            d["sample"] = short(val)

def walk(prefix, val, kind, acc):
    if isinstance(val, dict):
        if not val:
            acc.add(kind, prefix, {}); return
        for k, v in val.items():
            p = f"{prefix}.{k}" if prefix else k
            walk(p, v, kind, acc)
    elif isinstance(val, list):
        if not val:
            acc.add(kind, prefix + "[]", []); return
        for el in val:
            if isinstance(el, dict) and "type" in el and isinstance(el["type"], str):
                walk(f"{prefix}[{el['type']}]", el, kind, acc)
            elif isinstance(el, dict):
                walk(f"{prefix}[]", el, kind, acc)
            else:
                acc.add(kind, prefix + "[]", el)
    else:
        acc.add(kind, prefix, val)

def kind_of(obj, mode):
    if mode == "claude":
        return obj.get("type", "<no-type>")
    # cursor: role-based; note presence of 'type' too
    return "role:" + str(obj.get("role", obj.get("type", "<none>")))

def run(roots_glob, mode):
    acc = Acc()
    files = sorted(glob.glob(roots_glob, recursive=True))
    nrec = 0; nbad = 0
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        nbad += 1; continue
                    nrec += 1
                    if not isinstance(obj, dict):
                        acc.add("<non-dict-line>", "", obj); continue
                    kind = kind_of(obj, mode)
                    acc.kind_count[kind] += 1
                    for k, v in obj.items():
                        walk(k, v, kind, acc)
        except Exception as e:
            print(f"ERR {f}: {e}")
    print(f"### files={len(files)} records={nrec} bad_lines={nbad}")
    print(f"### record kinds: {dict(sorted(acc.kind_count.items(), key=lambda x:-x[1]))}")
    for kind in sorted(acc.data.keys(), key=lambda k: -acc.kind_count.get(k,0)):
        print(f"\n========== KIND: {kind}  (records={acc.kind_count.get(kind,0)}) ==========")
        for path in sorted(acc.data[kind].keys()):
            d = acc.data[kind][path]
            types = "/".join(sorted(d["types"]))
            print(f"  {path}  [{types}] x{d['count']}  e.g. {d['sample']}")

if __name__ == "__main__":
    mode = sys.argv[1]
    g = sys.argv[2]
    run(g, mode)
