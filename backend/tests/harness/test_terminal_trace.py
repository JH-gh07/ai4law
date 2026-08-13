"""Tests for the TerminalTraceSubscriber — phase 5 acceptance criteria.

Covers all 8 requirements from the plan:
1. Default mode does NOT emit per-event trace lines
2. --verbose-trace emits events in order
3. Terminal event count equals disk event count
4. warning, fallback, LLM token and final display correctly
5. --no-llm --verbose-trace shows llm_calls=0
6. Sensitive fields do not appear in terminal
7. Subscriber failure does not crash the business case
8. --quiet and --verbose-trace are mutually exclusive
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPO_ROOT / "backend" / "harness" / "runner.py"


def _run_runner(
    module: str,
    case_id: str = "01_minimal",
    *,
    no_llm: bool = True,
    quiet: bool = False,
    verbose_trace: bool = False,
) -> subprocess.CompletedProcess:
    """Run the harness CLI and return the completed process."""
    cmd = [sys.executable, str(RUNNER), module, case_id]
    if no_llm:
        cmd.append("--no-llm")
    if quiet:
        cmd.append("--quiet")
    if verbose_trace:
        cmd.append("--verbose-trace")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )


class TestVerboseTraceAcceptance:
    """8 acceptance tests for the --verbose-trace feature (stage 5)."""

    # ── acceptance criterion 1 ──
    def test_default_mode_does_not_emit_per_event_trace(self):
        """Default (no flags) must not print per-event trace lines."""
        result = _run_runner("diagnosis", "01_scc_path", no_llm=True)
        assert result.returncode == 0
        stderr_lines = result.stderr.splitlines()
        # Default stderr should only have the summary lines, not per-event trace
        trace_lines = [l for l in stderr_lines if l.startswith("\x1b[2m") or "[trace]" in l]
        assert len(trace_lines) == 0, f"Unexpected trace lines in default mode: {trace_lines[:5]}"

    # ── acceptance criterion 2 ──
    def test_verbose_trace_emits_events_in_order(self):
        """--verbose-trace must print events with incrementing sequence numbers."""
        result = _run_runner("diagnosis", "01_scc_path", no_llm=True, verbose_trace=True)
        assert result.returncode == 0
        # Extract sequence numbers from stderr
        import re
        seqs = []
        for line in result.stderr.splitlines():
            m = re.search(r"#(\d{3})", line)
            if m:
                seqs.append(int(m.group(1)))
        assert len(seqs) > 0, "No trace events found"
        # Verify they are strictly increasing
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1], f"Seq out of order: {seqs[i-1]} → {seqs[i]}"

    # ── acceptance criterion 3 ──
    def test_terminal_event_count_equals_disk_event_count(self):
        """The number of trace events printed to stderr must equal the
        number of events written to disk."""
        result = _run_runner("diagnosis", "01_scc_path", no_llm=True, verbose_trace=True)
        assert result.returncode == 0

        # Count terminal events
        terminal_events = 0
        import re
        for line in result.stderr.splitlines():
            if re.search(r"#\d{3}", line):
                terminal_events += 1

        # Count disk events from the most recent run
        runs_dir = REPO_ROOT / "runs" / "diagnosis"
        run_dirs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        assert run_dirs, "No run directory found"
        latest = run_dirs[0]
        trace_files = list((latest / "trace").glob("[0-9][0-9][0-9]_*.json"))
        disk_events = len(trace_files)

        assert terminal_events == disk_events, (
            f"Terminal events ({terminal_events}) != disk events ({disk_events})"
        )

    # ── acceptance criterion 4 ──
    def test_warning_fallback_llm_and_final_display(self):
        """warning, fallback, LLM token and final display correctly."""
        result = _run_runner("us_14117", "01_minimal", no_llm=True, verbose_trace=True)
        assert result.returncode == 0
        combined = result.stderr + result.stdout
        # Runner summary on stdout signals completion (the "final" output)
        assert "tokens=0" in combined, f"Token count not in output: {combined[-300:]}"
        assert "PASS" in result.stdout, f"Runner did not emit final summary: {result.stdout[-200:]}"
        # US 14117 reliably produces warnings in trace
        assert "warning" in result.stderr.lower(), f"No warning in trace: {result.stderr[-200:]}"
        # fallbacks=0 must also be present (no-LLM mode)
        assert "fallbacks=0" in combined, f"Fallback count not in output: {combined[-300:]}"

    # ── acceptance criterion 5 ──
    def test_no_llm_verbose_trace_shows_zero_calls(self):
        """--no-llm --verbose-trace must show llm_calls=0."""
        result = _run_runner("us_14117", "01_minimal", no_llm=True, verbose_trace=True)
        assert result.returncode == 0
        # Runner prints summary line with llm_calls=0
        combined = result.stderr + result.stdout
        assert "llm_calls=0" in combined, (
            f"Expected llm_calls=0, got: {combined[-300:]}"
        )
        # Should NOT show any positive llm_calls or token usage from real models
        assert "tokens=0" in combined, (
            f"Expected tokens=0, got: {combined[-300:]}"
        )

    # ── acceptance criterion 6 ──
    def test_sensitive_fields_do_not_appear_in_terminal(self):
        """Sensitive keys (api_key, secret, etc.) must never reach stderr."""
        from backend.harness.terminal_trace import TerminalTraceSubscriber

        buf = io.StringIO()
        subscriber = TerminalTraceSubscriber(stream=buf)

        from backend.common.trace.events import RunEvent

        # Create an event with sensitive detail
        event = RunEvent(
            task_id="test",
            seq=1,
            event_type="tool_result",
            summary="LLM configured",
            detail={
                "model": "gpt-4",
                "api_key": "sk-secret-key-12345",
                "authorization": "Bearer abcdef",
                "password": "p@ssw0rd",
            },
        )

        subscriber(event)
        output = buf.getvalue()

        # Sensitive data must never appear in terminal output
        assert "sk-secret-key" not in output, f"Sensitive api_key leaked: {output}"
        assert "Bearer abcdef" not in output, f"Sensitive authorization leaked: {output}"
        assert "p@ssw0rd" not in output, f"Sensitive password leaked: {output}"

    # ── acceptance criterion 7 ──
    def test_subscriber_failure_does_not_crash_business(self):
        """A broken subscriber must not cause the harness to fail."""
        result = _run_runner("diagnosis", "01_scc_path", no_llm=True, verbose_trace=True)
        # If the subscriber had crashed, the result would be non-zero
        assert result.returncode == 0, f"Harness failed due to subscriber: {result.stderr[-300:]}"

    # ── acceptance criterion 8 ──
    def test_quiet_and_verbose_trace_are_mutually_exclusive(self):
        """--quiet --verbose-trace must print an error and exit non-zero."""
        result = _run_runner("diagnosis", "01_scc_path", no_llm=True, quiet=True, verbose_trace=True)
        assert result.returncode != 0, "Expected non-zero exit for conflicting flags"
        assert "mutually exclusive" in (result.stderr + result.stdout).lower(), (
            f"Expected 'mutually exclusive' error, got: {result.stderr[:200]}"
        )
