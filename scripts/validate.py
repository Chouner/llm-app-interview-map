"""知识图谱校验：字段齐全、id 唯一、先修存在、无自环、无环，并输出统计。

用法：python scripts/validate.py [data/graph.json]
全部通过输出 VALIDATION PASSED，退出码 0；否则列出错误，退出码 1。
"""
import json
import sys
from collections import Counter, defaultdict

REQUIRED = ["id", "m", "name", "desc", "points", "pre", "src"]
STRENGTH = {"h", "s"}


def main(path="data/graph.json"):
    with open(path, encoding="utf-8") as f:
        g = json.load(f)

    errors = []
    modules = {m["id"]: m["name"] for m in g["modules"]}
    sources = set(g["sources"])
    nodes = g["nodes"]
    ids = [n.get("id") for n in nodes]

    for k, v in Counter(ids).items():
        if v > 1:
            errors.append(f"重复 id：{k}")
    idset = set(ids)

    for n in nodes:
        for key in REQUIRED:
            if key not in n:
                errors.append(f"{n.get('id')} 缺少字段 {key}")
        if n.get("m") not in modules:
            errors.append(f"{n['id']} 的模块 {n.get('m')} 不存在")
        if not n.get("points"):
            errors.append(f"{n['id']} 没有面试要点")
        for s in n.get("src", []):
            if s not in sources:
                errors.append(f"{n['id']} 的来源 {s} 未定义")
        for pid, strength in n.get("pre", []):
            if pid == n["id"]:
                errors.append(f"{n['id']} 自环")
            if pid not in idset:
                errors.append(f"{n['id']} 的先修 {pid} 不存在")
            if strength not in STRENGTH:
                errors.append(f"{n['id']} -> {pid} 强度 {strength} 非法")
        pre_ids = {p for p, _ in n.get("pre", [])}
        for wid in n.get("why", {}):
            if wid not in pre_ids:
                errors.append(f"{n['id']} 的 why 写了 {wid}，但它不是先修")
        mod = next((m for m in g["modules"] if m["id"] == n.get("m")), {})
        gids = {x["id"] for x in mod.get("groups", [])}
        if gids and n.get("g") not in gids:
            errors.append(f"{n['id']} 没有归到 {n.get('m')} 模块的分组里")
        if "depth" in n and len(n["depth"]) != 3:
            errors.append(f"{n['id']} 的 depth 应该有 3 级")

    # 环检测
    graph = {n["id"]: [p for p, _ in n.get("pre", []) if p in idset] for n in nodes}
    state = {}
    stack = []

    def dfs(u):
        state[u] = 1
        stack.append(u)
        for v in graph[u]:
            if state.get(v) == 1:
                cyc = stack[stack.index(v):] + [v]
                errors.append("存在环：" + " -> ".join(cyc))
            elif state.get(v) is None:
                dfs(v)
        stack.pop()
        state[u] = 2

    for u in graph:
        if state.get(u) is None:
            dfs(u)

    # 统计
    per_mod = Counter(n["m"] for n in nodes)
    edges = [(n["id"], p, s) for n in nodes for p, s in n.get("pre", [])]
    dependents = defaultdict(int)
    for _, p, _ in edges:
        dependents[p] += 1
    src_count = Counter(s for n in nodes for s in n["src"])
    roots = [n["id"] for n in nodes if not n["pre"]]
    leaves = [i for i in ids if dependents[i] == 0]

    print(f"知识点 {len(nodes)} 个，模块 {len(modules)} 个，先修边 {len(edges)} 条"
          f"（hard {sum(1 for e in edges if e[2] == 'h')}，soft {sum(1 for e in edges if e[2] == 's')}）")
    for mid, name in modules.items():
        print(f"  {name}：{per_mod[mid]}")
    print("来源：" + "，".join(f"{g['sources'][k]} {v}" for k, v in src_count.items()))
    print(f"根节点 {len(roots)} 个：{', '.join(roots)}")
    print(f"末端节点 {len(leaves)} 个")

    if errors:
        print("\n".join(["", "错误："] + errors))
        sys.exit(1)
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main(*sys.argv[1:])
