"""Raw measurement and replay lifecycle regressions."""

import copy

from cli_case import CliCase


class ReplayTests(CliCase):
    def test_replay_computes_raw_counts_and_delays_without_release(self):
        code, report = self.invoke()
        self.assertEqual(
            (
                code,
                report["replay"],
                report["release"],
                report["physical_authorization"],
            ),
            (0, "PASS", "HOLD", False),
        )
        observed = report["metrics"]
        self.assertEqual(
            (
                observed["duration_seconds"],
                observed["rendered_frames"],
                observed["lagged_frames"],
                observed["lag_percent"],
            ),
            (1800, 54000, 540, 1),
        )
        self.assertEqual(
            (
                observed["cue"]["count"],
                observed["cue"]["p95_ms"],
                observed["idle_dispatch"]["p95_ms"],
            ),
            (100, 200, 400),
        )
        self.assertEqual(
            (
                observed["provider"]["p95_ms"],
                observed["camera"]["p95_ms"],
                observed["encoder"]["p95_ms"],
            ),
            (800, 50, 100),
        )

    def test_faults_discard_pending_events_and_require_new_trigger_after_qualification(
        self,
    ):
        _, report = self.invoke()
        for result in report["faults"]:
            with self.subTest(fault=result["fault"]):
                expected = 1 if result["fault"] == "early_loss" else 2
                self.assertEqual(
                    (
                        result["dispatches"],
                        result["held_dispatches"],
                        result["stale_resume"],
                    ),
                    (expected, 3, False),
                )
                self.assertEqual(
                    result["fallback"],
                    "owner_override"
                    if result["fault"] == "owner_override"
                    else "fixed_rgb",
                )

    def test_missing_fault_or_incomplete_recovery_holds(self):
        for mutation, reason in (
            ("missing", "missing_fault:obs_stall"),
            ("recovery", "obs_stall:fault_lifecycle_incomplete"),
            ("clock", "obs_stall:nonmonotonic_fault_events"),
        ):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                if mutation == "missing":
                    data["faults"].pop(0)
                elif mutation == "recovery":
                    data["faults"][0]["events"] = [
                        event
                        for event in data["faults"][0]["events"]
                        if event["action"] != "recover"
                    ]
                else:
                    data["faults"][0]["events"][1]["at_ns"] = 0
                code, report = self.invoke(data=data)
                self.assertEqual(code, 2)
                self.assertIn(reason, report["holds"])

    def test_observed_lag_threshold_includes_two_percent_and_rejects_more(self):
        for lag, expected in ((36, 0), (37, 2)):
            with self.subTest(lag=lag):
                data = copy.deepcopy(self.data)
                for index, frame in enumerate(data["timings"]["frames"]):
                    frame["lagged"] = lag * index
                code, _ = self.invoke(data=data)
                self.assertEqual(code, expected)

    def test_nearest_rank_p95_and_idle_dispatch_selection(self):
        for tail, expected in ((5, 0), (6, 2)):
            with self.subTest(tail=tail):
                data = copy.deepcopy(self.data)
                for sample in data["timings"]["cues"][-tail:]:
                    sample["completed_ns"] = sample["received_ns"] + 251_000_000
                for sample in data["timings"]["motion"][-5:]:
                    sample["completed_ns"] = sample["received_ns"] + 900_000_000
                    sample["idle"] = False
                code, report = self.invoke(data=data)
                self.assertEqual(code, expected)
                self.assertEqual(
                    report["metrics"]["idle_dispatch"], {"count": 95, "p95_ms": 400}
                )
                self.assertEqual(
                    report["metrics"]["cue"]["p95_ms"], 200 if tail == 5 else 251
                )

    def test_timed_sample_failures_are_named_holds(self):
        mutations = (
            ("missing", "missing_cue_timed_samples"),
            ("early", "representative_duration_below_30_minutes"),
            ("reset", "frame_counter_gap_or_reset"),
            ("gap", "frame_counter_gap_or_reset"),
            ("negative", "invalid_cue_monotonic_samples"),
            ("outside", "cue_outside_frame_window"),
            ("no_idle", "idle_dispatch_p95_target_missed"),
            ("dispatch", "idle_dispatch_p95_target_missed"),
        )
        for mutation, reason in mutations:
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                times = data["timings"]
                if mutation == "missing":
                    times["cues"] = []
                elif mutation == "early":
                    times["frames"].pop()
                elif mutation == "reset":
                    times["frames"][3]["rendered"] = 0
                elif mutation == "gap":
                    times["frames"].pop(3)
                elif mutation == "negative":
                    times["cues"][0]["completed_ns"] = 0
                elif mutation == "outside":
                    times["cues"][-1]["completed_ns"] = 1900 * 10**9
                elif mutation == "no_idle":
                    for sample in times["motion"]:
                        sample["idle"] = False
                else:
                    for sample in times["motion"]:
                        sample["completed_ns"] = sample["received_ns"] + 501_000_000
                code, report = self.invoke(data=data)
                self.assertEqual(code, 2)
                self.assertIn(reason, report["holds"])

    def test_fault_trace_without_lost_dispatch_does_not_claim_coverage(self):
        data = copy.deepcopy(self.data)
        events = data["faults"][0]["events"]
        loss = next(
            index for index, event in enumerate(events) if event["action"] == "loss"
        )
        del events[loss + 1]
        code, report = self.invoke(data=data)
        self.assertEqual(code, 2)
        self.assertIn("obs_stall:resume_prerequisites_not_exercised", report["holds"])
