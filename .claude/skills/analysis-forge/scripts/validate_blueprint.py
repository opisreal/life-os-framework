#!/usr/bin/env python3
"""校验 SkillBlueprint（references/blueprint-schema.md 的 SkillBlueprint 契约）。

用法：
    python3 validate_blueprint.py <blueprint.json>
    cat blueprint.json | python3 validate_blueprint.py

退出码：0 = 通过；1 = 有 blocking 问题；2 = 输入/解析错误。
"""
import json
import re
import sys

REQUIRED_TOP = [
    "name", "params", "lenses", "synthesis_logic", "adversarial_check",
    "data_source_status", "output_format", "smoke_fixture",
]
REQUIRED_LENS = ["key", "data_sources", "frameworks", "produces"]
REQUIRED_PARAM = ["name", "required", "desc"]
REQUIRED_STATUS = ["name", "verification", "in_use"]
VERIFICATION_TIERS = {"discovered", "installable", "reachable", "sample_passed"}
# 占位/未完成标记；"..." 单独成值也算
PLACEHOLDER_RE = re.compile(r"TODO|FIXME|XXX|<占位|<placeholder|待定|待填", re.IGNORECASE)


def walk_strings(obj, path="$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")


def validate(bp):
    errors, warnings = [], []

    for f in REQUIRED_TOP:
        if f not in bp:
            errors.append(f"缺顶层字段: {f}")
    if errors:
        return errors, warnings  # 字段都不齐，后续检查无意义

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", bp["name"]):
        errors.append(f"name 不是 kebab-case: {bp['name']!r}")

    for i, p in enumerate(bp["params"]):
        for f in REQUIRED_PARAM:
            if f not in p:
                errors.append(f"params[{i}] 缺字段: {f}")
    if not bp["params"]:
        warnings.append("params 为空——确认这个 skill 真的无参数？（参数化优先，铁律 3）")

    status_by_name = {}
    for i, s in enumerate(bp["data_source_status"]):
        for f in REQUIRED_STATUS:
            if f not in s:
                errors.append(f"data_source_status[{i}] 缺字段: {f}")
        if s.get("verification") not in VERIFICATION_TIERS:
            errors.append(
                f"data_source_status[{i}] verification 非法: {s.get('verification')!r}"
            )
        if "name" in s:
            status_by_name[s["name"]] = s

    if not bp["lenses"]:
        errors.append("lenses 为空")
    for i, lens in enumerate(bp["lenses"]):
        for f in REQUIRED_LENS:
            if f not in lens:
                errors.append(f"lenses[{i}] 缺字段: {f}")
        for src in lens.get("data_sources", []):
            s = status_by_name.get(src)
            if s is None:
                errors.append(
                    f"lenses[{i}].data_sources 引用了状态表中不存在的源（虚构源风险）: {src!r}"
                )
            elif s.get("verification") != "sample_passed":
                errors.append(
                    f"lenses[{i}] 引用未验证源 {src!r}"
                    f"（档位 {s.get('verification')}，仅 sample_passed 可用，铁律 1）"
                )

    for path, s in walk_strings(bp):
        if PLACEHOLDER_RE.search(s):
            errors.append(f"占位/未完成标记 @ {path}: {s[:60]!r}")
        if s.strip() in {"...", "…", "?"}:
            errors.append(f"空洞值 @ {path}")

    if not str(bp["smoke_fixture"]).endswith(".md"):
        warnings.append(f"smoke_fixture 不像 markdown 路径: {bp['smoke_fixture']!r}")

    return errors, warnings


def main():
    try:
        raw = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
        bp = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"✗ 输入错误: {e}", file=sys.stderr)
        sys.exit(2)

    errors, warnings = validate(bp)
    for w in warnings:
        print(f"⚠ {w}")
    for e in errors:
        print(f"✗ {e}")
    if errors:
        print(f"\n{len(errors)} 个 blocking 问题")
        sys.exit(1)
    print("✓ blueprint 通过校验")


if __name__ == "__main__":
    main()
