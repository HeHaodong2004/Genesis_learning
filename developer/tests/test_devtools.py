"""Exercise user-visible contracts without importing the Genesis test fixtures."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "developer" / "gnav_dev.py"
spec = importlib.util.spec_from_file_location("gnav_dev", SCRIPT)
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


class ConfigPreflightTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="gnav-dev-test-")
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def config(self, text):
        path = self.root / "config.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_real_configuration_matches_original_loader(self):
        from gnav.config import load_config

        path = ROOT / "configs" / "eval.yaml"
        overrides = ["backend=cpu", "env.n_envs=2"]
        checked = dev.resolve_config(path, overrides)
        original = load_config(str(path), overrides)
        self.assertEqual(checked["config"], original.to_dict())
        self.assertEqual(checked["digest"], original.digest())
        self.assertEqual(checked["source"], str(ROOT / "src" / "gnav" / "config.py"))

    def test_inheritance_and_overrides_preserve_unspecified_fields(self):
        (self.root / "base.yaml").write_text("env:\n  n_envs: 4\n  sim_dt: 0.05\n")
        path = self.config("inherit: [base.yaml]\nname: child\nenv:\n  n_envs: 2\n")
        report = dev.resolve_config(path, ["env.n_envs=3"])
        self.assertEqual(report["config"]["env"]["n_envs"], 3)
        self.assertEqual(report["config"]["env"]["sim_dt"], 0.05)

    def test_missing_configuration(self):
        with self.assertRaisesRegex(dev.PreflightError, "找不到普通文件"):
            dev.resolve_config(self.root / "missing.yaml")

    def test_yaml_syntax_error(self):
        with self.assertRaisesRegex(dev.PreflightError, "YAML 无法解析"):
            dev.resolve_config(self.config("env: ["))

    def test_top_level_must_be_mapping(self):
        with self.assertRaisesRegex(dev.PreflightError, "顶层必须"):
            dev.resolve_config(self.config("[1, 2]"))

    def test_unknown_nested_key(self):
        with self.assertRaisesRegex(dev.PreflightError, "config.env.n_env：未知"):
            dev.resolve_config(self.config("env:\n  n_env: 2\n"))

    def test_bool_is_not_an_integer_count(self):
        with self.assertRaisesRegex(dev.PreflightError, "env.n_envs.*int"):
            dev.resolve_config(self.config("env:\n  n_envs: true\n"))

    def test_wrong_boolean_type_is_not_coerced(self):
        with self.assertRaisesRegex(dev.PreflightError, "depth_enabled.*bool"):
            dev.resolve_config(self.config("env:\n  sensors:\n    depth_enabled: maybe\n"))

    def test_nested_dataclass_cannot_be_null(self):
        with self.assertRaisesRegex(dev.PreflightError, "config.env：应为键值表"):
            dev.resolve_config(self.config("env: null\n"))

    def test_nonfinite_numeric_input(self):
        for value in (".nan", ".inf", "-.inf"):
            with self.subTest(value=value), self.assertRaisesRegex(dev.PreflightError, "sim_dt.*float"):
                dev.resolve_config(self.config(f"env:\n  sim_dt: {value}\n"))

    def test_untyped_custom_profile_rejects_nonfinite_values(self):
        for value in (".nan", ".inf", "-.inf"):
            with self.subTest(value=value), self.assertRaisesRegex(dev.PreflightError, "数值须有限"):
                dev.resolve_config(self.config("{}"), [
                    f"env.dynamics.custom_profiles={{custom: {{max_v: {value}}}}}",
                ])

    def test_untyped_custom_profile_rejects_yaml_alias_cycle(self):
        path = self.config("env:\n  dynamics:\n    custom_profiles:\n      custom: &cycle\n        nested: *cycle\n")
        with self.assertRaisesRegex(dev.PreflightError, "循环引用"):
            dev.resolve_config(path)

    def test_untyped_custom_profile_rejects_yaml_timestamp_object(self):
        path = self.config("env:\n  dynamics:\n    custom_profiles:\n      custom:\n        note: 2026-11-05\n")
        with self.assertRaisesRegex(dev.PreflightError, "可序列化的 JSON"):
            dev.resolve_config(path)

    def test_noncyclic_yaml_alias_is_supported(self):
        path = self.config("env:\n  dynamics:\n    custom_profiles:\n      custom: &profile {max_v: 1.0}\n      another: *profile\n")
        result = dev.resolve_config(path)
        profiles = result["config"]["env"]["dynamics"]["custom_profiles"]
        self.assertEqual(profiles["custom"], profiles["another"])
        json.dumps(result, allow_nan=False)

    def test_zero_and_negative_counts(self):
        for override in ("env.n_envs=0", "eval.n_episodes=-1", "train.checkpoint_every=0"):
            with self.subTest(override=override), self.assertRaisesRegex(dev.PreflightError, "必须 > 0"):
                dev.resolve_config(self.config("{}"), [override])

    def test_bad_backend(self):
        with self.assertRaisesRegex(dev.PreflightError, "backend 必须"):
            dev.resolve_config(self.config("backend: cuda"))

    def test_tuple_length(self):
        with self.assertRaisesRegex(dev.PreflightError, "需要 2 个元素"):
            dev.resolve_config(self.config("env:\n  sensors:\n    depth_res: [64]\n"))

    def test_full_circle_ray_field_is_supported(self):
        checked = dev.resolve_config(self.config("{}"), ["env.sensors.rays_fov_deg=360"])
        self.assertEqual(checked["config"]["env"]["sensors"]["rays_fov_deg"], 360)

    def test_negative_profile_probability(self):
        with self.assertRaisesRegex(dev.PreflightError, "概率不能为负"):
            dev.resolve_config(self.config("{}"), [
                "env.dynamics.profiles=[agile, heavy]", "env.dynamics.profile_probs=[-0.2, 1.2]",
            ])

    def test_profile_probability_length(self):
        with self.assertRaisesRegex(dev.PreflightError, "长度必须匹配"):
            dev.resolve_config(self.config("{}"), ["env.dynamics.profile_probs=[0.5, 0.5]"])

    def test_unknown_profile(self):
        with self.assertRaisesRegex(dev.PreflightError, "未知动力学"):
            dev.resolve_config(self.config("{}"), ["env.dynamics.profiles=[typo]"])

    def test_invalid_override_paths(self):
        for override in ("no_equals", "env..n_envs=2", "=2"):
            with self.subTest(override=override), self.assertRaisesRegex(dev.PreflightError, "section.key=value"):
                dev.resolve_config(self.config("{}"), [override])

    def test_override_cannot_descend_into_scalar(self):
        with self.assertRaisesRegex(dev.PreflightError, "无法应用覆盖参数"):
            dev.resolve_config(self.config("seed: 4"), ["seed.child=2"])

    def test_inherit_type(self):
        with self.assertRaisesRegex(dev.PreflightError, "inherit 必须"):
            dev.resolve_config(self.config("inherit: base.yaml"))

    def test_inheritance_cycle(self):
        path = self.config("inherit: [config.yaml]")
        with self.assertRaisesRegex(dev.PreflightError, "继承循环"):
            dev.resolve_config(path)

    def test_multiple_parents_match_original_merge_order(self):
        from gnav.config import load_config

        (self.root / "a.yaml").write_text("env:\n  n_envs: 4\n  sim_dt: 0.05\n")
        (self.root / "b.yaml").write_text("env:\n  n_envs: 5\n")
        path = self.config("inherit: [a.yaml, b.yaml]")
        self.assertEqual(dev.resolve_config(path)["config"], load_config(str(path)).to_dict())


class RunInspectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="gnav-run-test-")
        self.run = Path(self.directory.name) / "run"
        shutil.copytree(ROOT / "developer" / "fixtures" / "demo_run", self.run)

    def tearDown(self):
        self.directory.cleanup()

    def test_synthetic_fixture_and_read_only_behavior(self):
        before = {p.name: p.read_bytes() for p in self.run.iterdir()}
        report = dev.inspect_run(self.run)
        self.assertTrue(report["ok"])
        self.assertEqual(report["files"]["metrics.jsonl"]["records"], 2)
        self.assertTrue(report["files"]["provenance.json"]["summary"]["synthetic"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.run.iterdir()})

    def test_missing_run(self):
        with self.assertRaisesRegex(dev.PreflightError, "run 目录不存在"):
            dev.inspect_run(self.run / "missing")

    def test_missing_required_metadata(self):
        (self.run / "provenance.json").unlink()
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertIn("缺少 provenance.json", report["errors"])

    def test_missing_metrics(self):
        (self.run / "metrics.jsonl").unlink()
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertTrue(any("缺少 metrics.json" in error for error in report["errors"]))

    def test_bad_json_is_reported_not_a_traceback(self):
        (self.run / "provenance.json").write_text("{")
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertFalse(report["files"]["provenance.json"]["valid"])

    def test_jsonl_bad_line_has_location(self):
        (self.run / "metrics.jsonl").write_text('{"loss": 1}\n{bad\n')
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertIn("第 2 行", report["errors"][0])

    def test_empty_metrics_is_incomplete(self):
        (self.run / "metrics.jsonl").write_text("\n")
        self.assertFalse(dev.inspect_run(self.run)["ok"])

    def test_nonstandard_json_nan_rejected(self):
        (self.run / "metrics.json").write_text('{"loss": NaN}')
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertIn("非标准 JSON 数值 NaN", " ".join(report["errors"]))

    def test_json_exponent_overflow_is_reported(self):
        (self.run / "metrics.json").write_text('{"n_episodes": 1e400}')
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertIn("有限浮点范围", " ".join(report["errors"]))

    def test_metrics_digest_mismatch_detected(self):
        (self.run / "metrics.json").write_text('{"config_digest": "wrong"}')
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertIn("不匹配", " ".join(report["errors"]))

    def test_oversized_file_is_bounded(self):
        with (self.run / "metrics.json").open("wb") as stream:
            stream.truncate(dev.MAX_BYTES + 1)
        report = dev.inspect_run(self.run)
        self.assertFalse(report["ok"])
        self.assertIn("16 MiB", " ".join(report["errors"]))

    def test_checkpoint_and_arbitrary_provenance_fields_are_not_read(self):
        (self.run / "checkpoint.pt").write_bytes(b"not safe to deserialize")
        (self.run / "provenance.json").write_text(json.dumps({
            "git_commit": "fixture", "argv": ["--token=SECRET"], "api_key": "SECRET",
        }))
        report = dev.inspect_run(self.run)
        self.assertTrue(report["ok"])
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertNotIn("checkpoint.pt", report["files"])


class CliContractTests(unittest.TestCase):
    def run_cli(self, *args, cwd=ROOT):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                              capture_output=True, text=True, timeout=20)

    def test_doctor_json_and_worktree_origin(self):
        result = self.run_cli("doctor", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["checks"]["source_is_this_worktree"])
        self.assertEqual(report["root"], str(ROOT))

    def test_cli_config_error_exit_code(self):
        result = self.run_cli("config", "--config", "configs/eval.yaml", "env.n_envs=0", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_untyped_nan_and_alias_are_structured_input_errors(self):
        for override in (
            "env.dynamics.custom_profiles={custom: {max_v: .nan}}",
            "env.dynamics.custom_profiles={custom: &cycle {nested: *cycle}}",
        ):
            with self.subTest(override=override):
                result = self.run_cli("config", "--config", "configs/eval.yaml", override, "--json")
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json.loads(result.stdout)["ok"])
                self.assertNotIn("Traceback", result.stderr)

    def test_cli_successful_config(self):
        result = self.run_cli("config", "--config", "configs/eval.yaml", "backend=cpu", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["config"]["backend"], "cpu")

    def test_entrypoint_import_is_independent_of_cwd(self):
        result = self.run_cli("doctor", "--json", cwd="/tmp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["gnav_source"], str(ROOT / "src" / "gnav" / "__init__.py"))

    def test_all_tools_avoid_importing_heavy_modules(self):
        code = (
            "import runpy, sys; "
            f"m=runpy.run_path({str(SCRIPT)!r}); "
            "m['doctor'](); "
            f"m['resolve_config'](m['Path']({str(ROOT / 'configs/eval.yaml')!r})); "
            f"m['inspect_run'](m['Path']({str(ROOT / 'developer/fixtures/demo_run')!r})); "
            "assert 'torch' not in sys.modules; assert 'genesis' not in sys.modules"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
