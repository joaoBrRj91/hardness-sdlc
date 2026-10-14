#!/usr/bin/env python
"""Roda um comando e imprime só o resumo, sem gravar nada em disco.

Uso: python .claude/skills/task/scripts/qrun.py <rotulo> -- <comando...>

Sucesso: uma linha (ex.: "✔ dotnet test · 42 passed · 0 failed · 1 skipped · 3.2s").
Falha: "✖ <comando> · exit N" + até MAX_FAIL_LINES linhas relevantes.
O exit code do comando é preservado.
"""
import re
import subprocess
import sys
import time

MAX_FAIL_LINES = 40
MAX_PASSTHROUGH_LINES = 60
MAX_LINE_CHARS = 200

DOTNET_ALLOWED = {"build", "test", "format"}
GIT_ALLOWED = {"status", "diff", "log"}

TEST_LINE = re.compile(
    r"(?:Passed|Failed)!\s+-\s+Failed:\s*(\d+),\s*Passed:\s*(\d+),\s*Skipped:\s*(\d+),\s*Total:\s*(\d+)")
WARNINGS = re.compile(r"^\s*(\d+) Warning\(s\)", re.M)
ERRORS = re.compile(r"^\s*(\d+) Error\(s\)", re.M)
RELEVANT = re.compile(
    r" error |error [A-Z]+\d+|\bFailed\b|\[FAIL\]|Assert|Expected|Actual|Error Message|"
    r"Stack Trace|^\s+at .+ in .+:line \d+")


def allowed(argv):
    if len(argv) < 2:
        return False
    if argv[0] == "dotnet":
        return argv[1] in DOTNET_ALLOWED
    if argv[0] == "git":
        return argv[1] in GIT_ALLOWED
    return False


def clip(line):
    line = line.rstrip()
    return line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS - 1] + "…"


def relevant_lines(out):
    lines = out.splitlines()
    picked, seen = [], set()
    for i, line in enumerate(lines):
        if RELEVANT.search(line):
            for j in (i, i + 1):
                if j < len(lines) and j not in seen and lines[j].strip():
                    seen.add(j)
                    picked.append(clip(lines[j]))
    if not picked:
        picked = [clip(l) for l in lines[-15:] if l.strip()]
    # build multi-target repete o mesmo erro; remove duplicatas mantendo a ordem
    uniq = list(dict.fromkeys(picked))
    if len(uniq) > MAX_FAIL_LINES:
        omitted = len(uniq) - MAX_FAIL_LINES
        uniq = uniq[:MAX_FAIL_LINES] + [f"… {omitted} linhas omitidas"]
    return uniq


def success_line(argv, out, secs):
    label = " ".join(argv[:2])
    t = f"{secs:.1f}s"
    if argv[0] == "dotnet" and argv[1] == "test":
        rows = [tuple(map(int, m)) for m in TEST_LINE.findall(out)]
        if rows:
            failed = sum(r[0] for r in rows)
            passed = sum(r[1] for r in rows)
            skipped = sum(r[2] for r in rows)
            return f"✔ {label} · {passed} passed · {failed} failed · {skipped} skipped · {t}"
        return f"✔ {label} · sem resumo de testes · {t}"
    if argv[0] == "dotnet" and argv[1] == "build":
        w, e = WARNINGS.search(out), ERRORS.search(out)
        return f"✔ {label} · {e.group(1) if e else 0} erros · {w.group(1) if w else 0} avisos · {t}"
    if argv[0] == "dotnet":
        return f"✔ {label} · ok · {t}"
    return None  # git: passthrough truncado


def summarize(argv, rc, out, secs):
    """Texto a imprimir para o comando já executado."""
    label = " ".join(argv[:2])
    if rc == 0:
        line = success_line(argv, out, secs)
        if line:
            return line
        lines = [clip(l) for l in out.splitlines()]
        if len(lines) > MAX_PASSTHROUGH_LINES:
            omitted = len(lines) - MAX_PASSTHROUGH_LINES
            lines = lines[:MAX_PASSTHROUGH_LINES] + [f"… {omitted} linhas omitidas"]
        return "\n".join(lines) if lines else f"✔ {label} · sem saída · {secs:.1f}s"
    head = f"✖ {label} · exit {rc} · {secs:.1f}s"
    return "\n".join([head] + relevant_lines(out))


def main():
    args = sys.argv[1:]
    if "--" not in args:
        print("uso: qrun.py <rotulo> -- <comando...>", file=sys.stderr)
        return 2
    argv = args[args.index("--") + 1:]
    if not allowed(argv):
        print(f"qrun: comando fora da allowlist: {' '.join(argv)}. "
              "Permitidos: dotnet build|test|format, git status|diff|log.", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    start = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"✖ {argv[0]} · comando não encontrado")
        return 127
    out = (proc.stdout or "") + (proc.stderr or "")
    print(summarize(argv, proc.returncode, out, time.monotonic() - start))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
