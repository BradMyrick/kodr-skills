#!/usr/bin/env python3
"""Self-check for the kodr-skills library.

Enforces the repo's own conventions so drift cannot recur:
  1. Frontmatter: name == directory, version present, description present
     with a routing trigger ("use when/for/first/before/only after").
  2. Body: section-4 heading is exactly "### 4. Agent Execution Directives";
     code fences are balanced.
  3. Router closure (AGENTS.md): every routed skill exists; every skill is
     routed (cs-* papers are covered by the generic `cs-*` line).
  4. README: every skill has a table row; every row has a directory.
  5. Counts: any "<N> skills" stated in README.md / INSTALL.md matches reality.
  6. Reference code: every python fence parses; stdlib-only python fences
     with a __main__ guard are EXECUTED; stdlib-only rust fences are COMPILED.

Stdlib only. Exit 0 iff no failures.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []
CHECKS = 0

TRIGGER_RE = re.compile(r"use\s+(when|for|first|before|only\s+after)", re.I)
SKILL_DIR_RE = re.compile(r"^[a-z]+(-[a-z0-9]+)+$")
EXTERNAL_RUST_CRATES = {
    "tokio", "tokio_util", "capnp", "capnp_rpc", "proptest", "quickcheck",
    "thiserror", "anyhow", "eyre", "criterion", "rayon", "serde", "clap",
    "libfuzzer_sys", "cargo_fuzz", "crossbeam", "tracing", "log",
}


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def skill_dirs() -> list[Path]:
    return sorted(p for p in ROOT.iterdir() if (p / "SKILL.md").is_file())


def extract_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML frontmatter reader: scalar keys plus `>` folded scalars."""
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm: dict[str, str] = {}
    key: str | None = None
    for line in m.group(1).splitlines():
        km = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            key = km.group(1)
            fm[key] = km.group(2).strip().strip('"')
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " if fm[key] and fm[key] != ">" else "") + line.strip()
    return fm


def extract_fences(text: str, lang: str) -> list[str]:
    return [m.group(1) for m in re.finditer(rf"```{lang}\n(.*?)```", text, re.S)]


def check_frontmatter(dirs: list[Path]) -> None:
    global CHECKS
    for d in dirs:
        CHECKS += 1
        text = (d / "SKILL.md").read_text()
        if not re.match(r"\A---\n", text):
            fail(f"{d.name}: frontmatter must start at line 1 with ---")
            continue
        fm = extract_frontmatter(text)
        name, desc, ver = fm.get("name", ""), fm.get("description", ""), fm.get("version", "")
        if name != d.name:
            fail(f"{d.name}: frontmatter name {name!r} != directory {d.name!r}")
        if not ver:
            fail(f"{d.name}: missing version")
        if not desc or desc == ">":
            fail(f"{d.name}: missing description")
        elif not TRIGGER_RE.search(desc):
            fail(f"{d.name}: description lacks a routing trigger (Use when/for/first/before/only after)")
        # fences balanced
        n_fences = len(re.findall(r"^```", text, re.M))
        if n_fences % 2:
            fail(f"{d.name}: unbalanced code fences ({n_fences} markers)")
        # section-4 heading canonical (RFC-format skills only; `format: reference`
        # opts a curated/reference-layout skill out of the RFC body)
        if fm.get("format", "rfc") != "reference":
            headings = re.findall(r"^### 4\..*$", text, re.M)
            if headings != ["### 4. Agent Execution Directives"]:
                fail(f"{d.name}: section-4 heading is {headings!r}, expected '### 4. Agent Execution Directives'")
    ok(f"frontmatter/body conventions on {len(dirs)} skills")


def check_router(dirs: list[Path]) -> None:
    global CHECKS
    CHECKS += 1
    agents = (ROOT / "AGENTS.md").read_text()
    names = {d.name for d in dirs}
    # every routed skill exists
    for ref in set(re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", agents)):
        if SKILL_DIR_RE.match(ref) and ref not in names and "*" not in ref:
            fail(f"AGENTS.md routes `{ref}` but no such skill directory exists")
    # every skill is routed (cs-* covered by the generic pattern line)
    for name in sorted(names):
        if f"`{name}`" not in agents:
            if name.startswith("cs-") and "`cs-*`" in agents:
                continue
            fail(f"{name}: no routing line in AGENTS.md")
    ok("router <-> skill closure")


def check_readme_and_counts(dirs: list[Path]) -> None:
    global CHECKS
    CHECKS += 1
    readme = (ROOT / "README.md").read_text()
    install = (ROOT / "INSTALL.md").read_text() if (ROOT / "INSTALL.md").exists() else ""
    names = {d.name for d in dirs}
    for name in sorted(names):
        if f"`{name}`" not in readme:
            fail(f"{name}: no row in README.md")
    for ref in set(re.findall(r"\| `([a-z0-9]+(?:-[a-z0-9]+)+)` \|", readme)):
        if ref not in names:
            fail(f"README.md lists `{ref}` but no such skill directory exists")
    actual = len(names)
    for fname, text in (("README.md", readme), ("INSTALL.md", install)):
        for m in re.finditer(r"\b(\d+)\s+skills?\b", text):
            if int(m.group(1)) != actual:
                fail(f"{fname}: says '{m.group(0)}' but the repo has {actual}")
    ok(f"README rows + stated counts match reality ({actual} skills)")


def python_stdlib_only(code: str) -> bool:
    for m in re.finditer(r"^\s*(?:import|from)\s+([a-zA-Z_][\w.]*)", code, re.M):
        root = m.group(1).split(".")[0]
        if root not in sys.stdlib_module_names:
            return False
    return True


def check_python_fences(dirs: list[Path]) -> None:
    global CHECKS
    ran = failed = 0
    for d in dirs:
        text = (d / "SKILL.md").read_text()
        for i, code in enumerate(extract_fences(text, "python")):
            CHECKS += 1
            tag = f"{d.name} python fence #{i + 1}"
            try:
                ast.parse(code)
            except SyntaxError as e:
                fail(f"{tag}: SyntaxError {e}")
                continue
            if "__main__" in code and python_stdlib_only(code):
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                    f.write(code)
                try:
                    r = subprocess.run([sys.executable, f.name], capture_output=True, timeout=20)
                    if r.returncode != 0:
                        failed += 1
                        fail(f"{tag}: exits {r.returncode}: {r.stderr.decode()[-300:]}")
                    else:
                        ran += 1
                except subprocess.TimeoutExpired:
                    failed += 1
                    fail(f"{tag}: timed out")
    ok(f"python fences: {ran} executed clean, {failed} failed")


# A fence starting a line at column 0 with a statement keyword is an excerpt
# (rustfmt indents statements inside fns), not a whole program: syntax-illustration only.
RUST_FRAGMENT_RE = re.compile(r"^(let|if|while|return|for|match)\b", re.M)


def rust_stdlib_only(code: str) -> bool:
    if "env!(\"OUT_DIR\")" in code:  # cargo build-script codegen pattern
        return False
    if any(re.search(rf"\b{c}\b", code) for c in EXTERNAL_RUST_CRATES):
        return False
    for m in re.finditer(r"^\s*use\s+([a-z_][a-z0-9_]*)", code, re.M):
        if m.group(1) not in ("std", "core", "alloc", "self", "super", "crate"):
            return False
    return True


def check_rust_fences(dirs: list[Path]) -> None:
    global CHECKS
    if not shutil.which("rustc"):
        print("skip  rust fences (rustc not installed)")
        return
    compiled = failed = skipped = 0
    with tempfile.TemporaryDirectory() as td:
        for d in dirs:
            text = (d / "SKILL.md").read_text()
            for i, code in enumerate(extract_fences(text, "rust")):
                CHECKS += 1
                tag = f"{d.name} rust fence #{i + 1}"
                if not rust_stdlib_only(code) or RUST_FRAGMENT_RE.search(code):
                    skipped += 1
                    continue
                src = Path(td) / "main.rs"
                out = Path(td) / "out.rlib"
                src.write_text(code)
                r = subprocess.run(
                    ["rustc", "--edition", "2021", "--crate-type", "lib",
                     "-A", "dead_code", "-A", "unused_variables", "-A", "unused_imports",
                     "-o", str(out), str(src)],
                    capture_output=True, timeout=60,
                )
                if r.returncode != 0:
                    failed += 1
                    first = r.stderr.decode().splitlines()
                    fail(f"{tag}: rustc error: {next((l for l in first if l.startswith('error')), first[:1])}")
                else:
                    compiled += 1
    ok(f"rust fences: {compiled} compiled, {skipped} skipped (external crates), {failed} failed")


def main() -> int:
    dirs = skill_dirs()
    if not dirs:
        fail("no skill directories found")
    print(f"== kodr-skills self-check: {len(dirs)} skills ==\n")

    check_frontmatter(dirs)
    check_router(dirs)
    check_readme_and_counts(dirs)
    check_python_fences(dirs)
    check_rust_fences(dirs)

    print(f"\n== {CHECKS} checks: {len(FAILURES)} failures ==")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
