"""Exact-uv regressions for the accepted network provisioning entrypoint.

Run only in a credential-free restricted worker. Fixtures use only empty projects
and synthetic local wheels; UV_OFFLINE prevents package-registry access.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "tools/ci/provision-python.sh"
SERVICES = ("embodiment-gateway", "hermes-activity", "stream-supervisor")


class PythonProvisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable = shutil.which("uv")
        if not executable:
            raise unittest.SkipTest("Exact uv 0.13.6 unavailable; provisioning regression not exercised")
        cls.uv = str(Path(executable).resolve())
        result = subprocess.run([cls.uv, "--version"], capture_output=True, text=True, check=True)
        if result.stdout.split()[:2] != ["uv", "0.13.6"]:
            raise unittest.SkipTest("Requires exact uv 0.13.6; found " + result.stdout.strip())
        cls.python = str(Path(sys.executable).resolve())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.source = self.base / "source"
        self.source.mkdir()
        self.env = {"PATH": "/usr/bin:/bin", "HOME": str(self.base),
                    "UV_OFFLINE": "1", "UV_PYTHON_DOWNLOADS": "never"}
        for name in SERVICES:
            project = self.source / "services" / name
            project.mkdir(parents=True)
            (project / "pyproject.toml").write_text(
                '[project]\nname = "' + name + '"\nversion = "0.1.0"\n'
                'requires-python = ">=3.9"\ndependencies = []\n')
            self.lock("--project", project)
        self.script = self.source / "services/camera-capture/tests/test_snapshot.py"
        self.script.parent.mkdir(parents=True)
        self.script.write_text('# /// script\n# requires-python = ">=3.9"\n# dependencies = []\n# ///\nraise RuntimeError("candidate script executed")\n')
        self.lock("--script", self.script)

    def lock(self, flag, path):
        subprocess.run([self.uv, "--no-config", "lock", "--python", self.python,
                        flag, str(path)], cwd=self.base, env=self.env,
                       capture_output=True, text=True, check=True, timeout=30)

    def provision(self):
        return subprocess.run(["/bin/bash", str(HELPER), str(self.source),
                               str(self.base / "python-envs"), str(self.base / "cache"),
                               self.uv, self.python], cwd=self.base, env=self.env,
                              capture_output=True, text=True, timeout=30)

    def ready(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in SERVICES:
            python = self.base / "python-envs" / name / "bin/python"
            self.assertTrue(python.is_file(), str(python))
            # This readiness probe is test-only and offline, after provisioning.
            subprocess.run([str(python), "-I", "-c", "import sys; assert sys.prefix != sys.base_prefix"],
                           env=self.env, cwd=self.base, check=True, timeout=5)
        self.assertTrue((self.base / "cache").is_dir())

    def test_benign_empty_projects_are_ready(self):
        self.ready(self.provision())

    def test_candidate_interpreters_and_configuration_never_execute(self):
        marker = self.base / "candidate-executed"
        evil = self.source / "evil-python"
        evil.write_text('#!/bin/sh\n: > "' + str(marker) + '"\nexit 97\n')
        evil.chmod(0o700)
        startup = 'from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n'
        (self.source / "sitecustomize.py").write_text(startup)
        self.env.update({"PYTHONPATH": str(self.source), "UV_PYTHON": str(evil),
                         "VIRTUAL_ENV": str(self.source / "selected-env"),
                         "UV_PROJECT_ENVIRONMENT": str(self.source / "selected-env"),
                         "UV_CONFIG_FILE": str(self.source / "uv.toml")})
        (self.source / "uv.toml").write_text('python = "' + str(evil) + '"\n')
        (self.source / ".python-version").write_text(str(evil) + "\n")
        for name in SERVICES:
            project = self.source / "services" / name
            (project / ".python-version").write_text(str(evil) + "\n")
            (project / "uv.toml").write_text('python = "' + str(evil) + '"\n')
            venv = project / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "bin/python").symlink_to(evil)
            (venv / "pyvenv.cfg").write_text('home = ' + str(evil.parent) + '\n')
            (project / "sitecustomize.py").write_text(startup)
        (self.script.parent / ".python-version").write_text(str(evil) + "\n")
        (self.script.parent / "uv.toml").write_text('python = "' + str(evil) + '"\n')
        self.ready(self.provision())
        self.assertFalse(marker.exists(), "candidate interpreter/startup executed")

    def test_installed_pth_runs_only_after_provisioning(self):
        marker = self.base / "dependency-startup"
        wheel = self.base / "startup_probe-1.0-py3-none-any.whl"
        info = "startup_probe-1.0.dist-info/"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("startup_probe.pth", "import pathlib; pathlib.Path(" + repr(str(marker)) + ").touch()\n")
            archive.writestr(info + "METADATA", "Metadata-Version: 2.1\nName: startup-probe\nVersion: 1.0\n")
            archive.writestr(info + "WHEEL", "Wheel-Version: 1.0\nGenerator: regression\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
            archive.writestr(info + "RECORD", "")
        for name in SERVICES:
            project = self.source / "services" / name
            metadata = project / "pyproject.toml"
            metadata.write_text(metadata.read_text().replace('dependencies = []',
                'dependencies = ["startup-probe @ ' + wheel.as_uri() + '"]'))
            self.lock("--project", project)
        result = self.provision()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(marker.exists(), "installed dependency startup ran during provisioning")
        # Deliberately run only after provisioning, in this network-denied test.
        self.ready(result)
        self.assertTrue(marker.exists(), "fixture must actually execute at interpreter startup")

    def test_prepared_script_cache_is_reused_offline(self):
        marker = self.base / "script-completed"
        wheel = self.base / "snapshot_probe-1.0-py3-none-any.whl"
        info = "snapshot_probe-1.0.dist-info/"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("snapshot_probe.py", "VALUE = 42\n")
            archive.writestr(info + "METADATA", "Metadata-Version: 2.1\nName: snapshot-probe\nVersion: 1.0\n")
            archive.writestr(info + "WHEEL", "Wheel-Version: 1.0\nGenerator: regression\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
            archive.writestr(info + "RECORD", "")
        self.script.write_text(
            '# /// script\n# requires-python = ">=3.9"\n'
            '# dependencies = ["snapshot-probe @ ' + wheel.as_uri() + '"]\n# ///\n'
            'import sys\nfrom pathlib import Path\nfrom snapshot_probe import VALUE\n'
            'assert VALUE == 42\nPath(' + repr(str(marker)) + ').write_text(sys.prefix)\n')
        self.lock("--script", self.script)
        result = self.provision()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(marker.exists(), "provisioning executed the script")
        cache = self.base / "cache"
        prepared = {path.parent.resolve() for path in cache.rglob("pyvenv.cfg")}
        self.assertTrue(prepared, "provisioning did not prepare a script environment")
        result = subprocess.run(
            [self.uv, "--no-config", "--offline", "run", "--python", self.python,
             "--frozen", "--script", str(self.script)],
            cwd=self.base, env={**self.env, "UV_CACHE_DIR": str(cache)},
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(marker.exists(), "offline fixture did not finish")
        self.assertIn(Path(marker.read_text()).resolve(), prepared,
                      "offline script did not use the previously prepared environment")

    def test_reused_or_symlink_state_fails_closed(self):
        for target in ("python-envs", "cache"):
            for symlink in (False, True):
                with self.subTest(target=target, symlink=symlink):
                    path = self.base / target
                    if symlink:
                        path.symlink_to(self.source, target_is_directory=True)
                    else:
                        path.mkdir()
                    result = self.provision()
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    for state in ("python-envs", "cache"):
                        item = self.base / state
                        if item.is_symlink():
                            item.unlink()
                        elif item.exists():
                            shutil.rmtree(item)

    def test_project_symlink_escape_rejected(self):
        project = self.source / "services" / SERVICES[0]
        outside = self.base / "outside"
        project.rename(outside)
        project.symlink_to(outside, target_is_directory=True)
        result = self.provision()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Project escapes candidate", result.stderr)


if __name__ == "__main__":
    unittest.main()
