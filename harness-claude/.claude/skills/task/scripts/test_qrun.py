"""Testes do qrun.py. Rode: python -m unittest discover -s .claude/skills/task/scripts"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import qrun  # noqa: E402

TEST_OK = """
Passed!  - Failed:     0, Passed:    30, Skipped:     1, Total:    31, Duration: 2 s - A.Tests.dll (net10.0)
Passed!  - Failed:     0, Passed:    12, Skipped:     0, Total:    12, Duration: 1 s - B.Tests.dll (net10.0)
"""

TEST_FAIL = """
  Failed Orders.Tests.CreateOrder_Rejects_Empty [12 ms]
  Error Message:
   Assert.Equal() Failure: Values differ
   Expected: 1
   Actual:   0
  Stack Trace:
     at Orders.Tests.CreateOrder_Rejects_Empty() in /src/Orders.Tests/OrderTests.cs:line 42
Failed!  - Failed:     1, Passed:    41, Skipped:     0, Total:    42, Duration: 3 s - A.Tests.dll (net10.0)
"""

BUILD_OK = """
Build succeeded.
    2 Warning(s)
    0 Error(s)
Time Elapsed 00:00:04.12
"""

BUILD_FAIL = """
/src/A/Foo.cs(10,5): error CS1002: ; expected [/src/A/A.csproj]
/src/A/Foo.cs(10,5): error CS1002: ; expected [/src/A/A.csproj]
Build FAILED.
    0 Warning(s)
    1 Error(s)
"""


class SummarizeTest(unittest.TestCase):
    def test_test_success_sums_assemblies(self):
        out = qrun.summarize(["dotnet", "test"], 0, TEST_OK, 3.2)
        self.assertEqual(out, "✔ dotnet test · 42 passed · 0 failed · 1 skipped · 3.2s")

    def test_test_failure_shows_only_relevant_lines(self):
        out = qrun.summarize(["dotnet", "test"], 1, TEST_FAIL, 3.0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "✖ dotnet test · exit 1 · 3.0s")
        self.assertTrue(any("Expected: 1" in l for l in lines))
        self.assertTrue(any("OrderTests.cs:line 42" in l for l in lines))
        self.assertLessEqual(len(lines), qrun.MAX_FAIL_LINES + 2)

    def test_build_success(self):
        out = qrun.summarize(["dotnet", "build"], 0, BUILD_OK, 4.1)
        self.assertEqual(out, "✔ dotnet build · 0 erros · 2 avisos · 4.1s")

    def test_build_failure_dedupes_errors(self):
        out = qrun.summarize(["dotnet", "build"], 1, BUILD_FAIL, 1.0)
        self.assertEqual(out.count("CS1002"), 1)

    def test_failure_is_capped(self):
        noisy = "\n".join(f"x.cs({i},1): error CS{i:04d}: boom" for i in range(200))
        lines = qrun.summarize(["dotnet", "build"], 1, noisy, 1.0).splitlines()
        self.assertLessEqual(len(lines), qrun.MAX_FAIL_LINES + 2)
        self.assertIn("linhas omitidas", lines[-1])

    def test_git_passthrough_truncated(self):
        out = qrun.summarize(["git", "log"], 0, "\n".join(["l"] * 200), 0.1)
        self.assertIn("140 linhas omitidas", out)


class AllowlistTest(unittest.TestCase):
    def test_allowed(self):
        self.assertTrue(qrun.allowed(["dotnet", "test", "--filter", "X"]))
        self.assertTrue(qrun.allowed(["git", "status"]))

    def test_refused(self):
        self.assertFalse(qrun.allowed(["rm", "-rf", "x"]))
        self.assertFalse(qrun.allowed(["dotnet", "publish"]))
        self.assertFalse(qrun.allowed(["git", "push"]))
        self.assertFalse(qrun.allowed(["dotnet"]))


class CliTest(unittest.TestCase):
    script = os.path.join(os.path.dirname(__file__), "qrun.py")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, self.script, *args],
                              capture_output=True, text=True, encoding="utf-8")

    def test_refuses_and_exit_code(self):
        r = self.run_cli("x", "--", "rm", "-rf", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("fora da allowlist", r.stderr)

    def test_preserves_exit_code_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, self.script, "s", "--", "git", "status"],
                               capture_output=True, text=True, encoding="utf-8", cwd=d)
            self.assertEqual(r.returncode, 128)  # fora de um repo git
            self.assertEqual(os.listdir(d), [])


if __name__ == "__main__":
    unittest.main()
