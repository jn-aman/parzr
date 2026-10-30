"""Shared helpers for the quality runners: latency and memory measurement, sealed test sets and the committed baselines.

benchmarks/baselines.json holds the last accepted numbers of every gated suite (scripts/update-baselines.py writes it,
on purpose, from summaries). A runner given a suite name compares its summary with that entry and fails when
  - a fix rate (the tone regression set: a mode's pass rate) drops more than `fix_rate_points` percentage points below the baseline
    (`RATE_TOLERANCE_POINTS` widens that for a suite whose answers differ between machines: tone-regression-2 and tone-regression-3, 4 points each),
  - false alarms (or damaged names) rise by more than `false_alarm_items` items,
  - p50 or p95 latency, or the engine's peak memory, exceeds the baseline times `performance_factor`
    (latency also gets `latency_slack_ms`), compared only with a performance baseline measured on the same kind
    of machine (`machine()`: "ci" or the local chip). Outside CI a slower run only warns: a laptop is shared with
    other work, a CI runner is not.
Engines under test run with an empty HOME (`engine_env`) so the writer's known words never change a score.
"""
import json, os, pathlib, platform, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINES = ROOT / 'benchmarks/baselines.json'
# Suites whose p50/p95 latency comparison is informational: it prints the same line but never fails the run (peak memory and pass
# rates stay hard gates). On the GPU-less CI runner the 0.8B tone model's latency varies by more than 1.5x between identical runs
# (PR #41: Direct p95 22.7 s, 25.5 s and 21.1 s on the same code against a 16.0 s single-run baseline), and a 52-item sample's p95
# is its third slowest item. Tone latency is measured locally (summary.json p50/p95); the everyday gate covers Fix-mode latency.
LATENCY_INFORMATIONAL = ('tone-regression', 'tone-regression-2', 'tone-regression-3')
# Per-suite pass-rate tolerance in percentage points, replacing `tolerance.fix_rate_points` for that suite. The second tone set is
# the measurement of generalisation, so its 50-item sample sits on the model's borderline items: the 0.8B model's greedy answers
# differ between a Mac and the runner there, and one or two verdicts move either way (CI run 41006663116: six verdicts flipped,
# professional 38/50 locally against 36/50 on the runner). The third tone set is a sample of the same size and the same kind of
# measurement, so it gets the same tolerance. 4.0 points is two items of fifty.
RATE_TOLERANCE_POINTS = {'tone-regression-2': 4.0, 'tone-regression-3': 4.0}


_HOME = None


def engine_env(base=None):
    """The environment for an engine under test: HOME points at an empty folder, so the writer's own known words
    (~/Library/Application Support/Parzr/known-words.json) never change a score and a local run matches CI. The model
    packs stay where they were (PARZR_MODELS_DIR, else the app's folder in the real home). PARZR_USE_HOME=1 keeps HOME."""
    global _HOME
    env = dict(os.environ if base is None else base)
    if env.get('PARZR_USE_HOME') == '1' or not env.get('HOME'):
        return env
    if _HOME is None:
        import atexit, shutil, tempfile
        _HOME = tempfile.mkdtemp(prefix='parzr-gate-home-')
        atexit.register(shutil.rmtree, _HOME, True)
    env.setdefault('PARZR_MODELS_DIR', os.path.join(env['HOME'], 'Library/Application Support/Parzr/Models'))
    env['HOME'] = _HOME
    return env


def release_gate():
    """True on CI or when the owner runs a release gate on purpose (PARZR_RELEASE_GATE=1)."""
    return os.environ.get('CI') == 'true' or os.environ.get('PARZR_RELEASE_GATE') == '1'


def machine():
    """The performance baseline this run is compared with: 'ci' on GitHub's runners, else the local chip."""
    if os.environ.get('CI') == 'true':
        return 'ci'
    try:
        chip = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()
    except OSError:
        chip = ''
    return 'local-' + re.sub(r'[^a-z0-9]+', '-', (chip or platform.machine()).lower()).strip('-')


def percentile(values, q):
    values = sorted(values)
    if not values:
        return 0.0
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def latency(ms):
    return {'p50_ms': round(percentile(ms, .5), 2), 'p95_ms': round(percentile(ms, .95), 2), 'max_ms': round(max(ms, default=0), 2), 'n': len(ms)}


def reap(proc):
    """Wait for a child whose stdin is closed and return its peak resident memory in MB (os.wait4's rusage:
    bytes on macOS, KB on Linux). None when the child was already reaped."""
    try:
        _, status, usage = os.wait4(proc.pid, 0)
        proc.returncode = os.waitstatus_to_exitcode(status)
    except ChildProcessError:
        proc.wait(timeout=30)
        return None
    scale = 1 if sys.platform == 'darwin' else 1024
    return round(usage.ru_maxrss * scale / 1e6, 1)


def load():
    return json.loads(BASELINES.read_text()) if BASELINES.exists() else {'suites': {}, 'performance': {}}


class Gate:
    """Collects baseline failures for one suite; `finish()` prints them and says whether the run passed."""

    def __init__(self, suite, baselines=None):
        self.suite, self.data = suite, baselines or load()
        self.tolerance = self.data.get('tolerance', {})
        self.base = self.data.get('suites', {}).get(suite)
        self.failures, self.notes = [], []
        if self.base is None:
            self.failures.append(f'{suite}: no baseline in {BASELINES.relative_to(ROOT)} (record one with scripts/update-baselines.py)')

    def rate(self, name, fixed, n, base_fixed, base_n):
        points = RATE_TOLERANCE_POINTS.get(self.suite, self.tolerance.get('fix_rate_points', 0.5))
        now, then = 100 * fixed / max(1, n), 100 * base_fixed / max(1, base_n)
        line = f'{self.suite} {name}: {fixed}/{n} = {now:.2f}% (baseline {then:.2f}%)'
        if now < then - points:
            self.failures.append(f'{line} dropped more than {points} points')
        else:
            self.notes.append(line)

    def count(self, name, value, base_value):
        items = self.tolerance.get('false_alarm_items', 2)
        line = f'{self.suite} {name}: {value} (baseline {base_value})'
        if value > base_value + items:
            self.failures.append(f'{line} rose by more than {items}')
        else:
            self.notes.append(line)

    def performance(self, key, measured):
        """measured: {'p50_ms', 'p95_ms', 'max_rss_mb'}; compared with performance[machine()][suite/key]."""
        where = machine()
        base = self.data.get('performance', {}).get(where, {}).get(f'{self.suite}/{key}')
        if not base:
            self.notes.append(f'{self.suite}/{key}: no {where} performance baseline yet; measured {measured}')
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                print(f'::warning::{self.suite}/{key}: no {where} performance baseline yet (measured {measured}); record it with '
                      f'scripts/update-baselines.py {self.suite} SUMMARY --performance-only from this run\'s quality-summaries artifact')
            return
        factor = self.tolerance.get('performance_factor', 1.5)
        # Sub-millisecond rules checks jitter by more than half their time: latency also gets a small absolute allowance.
        slack = {'p50_ms': self.tolerance.get('latency_slack_ms', 2), 'p95_ms': self.tolerance.get('latency_slack_ms', 2), 'max_rss_mb': 0}
        for metric in ('p50_ms', 'p95_ms', 'max_rss_mb'):
            if base.get(metric) is None or measured.get(metric) is None:
                continue
            line = f'{self.suite}/{key} {metric}: {measured[metric]} (baseline {base[metric]} on {where})'
            if measured[metric] > max(base[metric] * factor, base[metric] + slack[metric]):
                if metric != 'max_rss_mb' and self.suite in LATENCY_INFORMATIONAL:
                    self.notes.append(f'{line} is more than {factor}x the baseline (over baseline, informational: tone latency never fails a run)')
                    continue
                # A dedicated CI runner fails; a local run shares the machine with other work, so it only warns.
                (self.failures if release_gate() else self.notes).append(
                    f'{line} is more than {factor}x the baseline' + ('' if release_gate() else ' (warning only outside CI)'))
            else:
                self.notes.append(line)

    def finish(self):
        for note in self.notes:
            print(f'  baseline ok: {note}')
        for failure in self.failures:
            print(f'BASELINE FAILED: {failure}', file=sys.stderr)
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                print(f'::error::{failure}')
        return not self.failures
