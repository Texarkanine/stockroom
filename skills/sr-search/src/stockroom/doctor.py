"""Read-only environment diagnostics (``python -m stockroom.doctor``).

The Phase-3 m3 diagnostic surface behind ``sr-initialize``. Two actions,
both constitutionally read-only (they never install, sync, or write):

* ``probe`` — torch-free environment facts: OS/arch (``platform``), GPU
  name / driver / driver-CUDA ceiling / compute capability (``nvidia-smi``
  in its stable ``--query-gpu=`` CSV mode; absence or failure is a
  *reported fact*, never an error), torch import state, the engine
  directory, and the resolved warehouse home / how it was chosen
  (``home`` / ``home-source``). Facts only — the torch-wheel recommendation
  mapping is judgment and lives in the ``sr-initialize`` skill prose.
* ``smoke`` — the loud-failing torch/encoder verification: prints
  ``torch.__version__`` and ``torch.cuda.is_available()``, then encodes one
  string through the production :class:`stockroom.embed.BgeEncoder` path
  and checks the vector width. Exit 0 with an ``ok`` summary, or exit 1
  with exactly one stderr line that always carries the *next action*
  (the errmsg ratchet: torch-missing names the engine environment and
  either ``stockroom shim ensure-env`` when a usable freeze exists or the
  literal provisioning command otherwise; encode failures name the
  re-pick remedy).

Testability follows the engine-wide injection precedent: ``probe_facts``
takes an injectable ``nvidia-smi`` runner and torch importer (so it is
fully covered torch-free), ``run_smoke`` takes an injectable torch importer
and encoder factory (the real-model path is the one
``importorskip("torch")``-gated test).

Design record: ``memory-bank/active/creative/creative-onboarding-logic-surface.md``.
"""

import argparse
import importlib
import platform
import subprocess
import sys
from collections.abc import Callable

from stockroom.embed import EMBED_DIM, BgeEncoder, Encoder
from stockroom.shim import default_app_dir
from stockroom.torch_source import read_freeze_path
from stockroom.warehouse import resolve_home

#: The wheel-index base every torch remedy points at. The concrete build
#: (``cu126``, ``cpu``, …) is a per-machine human choice made in
#: ``sr-initialize`` — the remedy names the command shape, not the wheel.
_TORCH_INDEX_BASE = "https://download.pytorch.org/whl"

#: An injectable runner for ``nvidia-smi``: takes the argument list (after
#: the executable) and returns stdout text, raising on any failure
#: (``FileNotFoundError`` when the binary is absent).
SmiRunner = Callable[[list[str]], str]

#: An injectable importer with the :func:`importlib.import_module` signature.
Importer = Callable[[str], object]


def _run_nvidia_smi(args: list[str]) -> str:
    """Run ``nvidia-smi`` with ``args``; return stdout or raise on failure."""
    return subprocess.run(
        ["nvidia-smi", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout


def _gpu_facts(smi_runner: SmiRunner) -> list[tuple[str, str]]:
    """Return the GPU fact pairs, degrading every failure to a fact.

    Uses ``nvidia-smi``'s stable ``--query-gpu=`` CSV mode for the per-GPU
    fields and the ``--version`` banner for the driver's CUDA ceiling (the
    CSV query set has no cuda_version field). Absent binary → ``gpu: none``;
    any error or unparseable output → ``gpu: unavailable``.
    """
    try:
        csv = smi_runner(
            ["--query-gpu=name,driver_version,compute_cap", "--format=csv,noheader"]
        )
    except FileNotFoundError:
        return [("gpu", "none")]
    except Exception:
        return [("gpu", "unavailable")]

    first_line = csv.strip().splitlines()[0] if csv.strip() else ""
    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) != 3 or not all(parts):
        return [("gpu", "unavailable")]
    name, driver, compute_cap = parts

    facts = [("gpu", name), ("driver", driver), ("gpu-compute-cap", compute_cap)]
    try:
        banner = smi_runner(["--version"])
    except Exception:
        return facts
    for line in banner.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower().startswith("cuda version") and value.strip():
            facts.insert(2, ("driver-cuda", value.strip()))
            break
    return facts


def _torch_facts(torch_importer: Importer) -> list[tuple[str, str]]:
    """Return the torch import-state fact pairs (never raises)."""
    try:
        torch = torch_importer("torch")
    except Exception:
        return [("torch", "not installed")]
    version = str(getattr(torch, "__version__", "unknown"))
    try:
        cuda = str(torch.cuda.is_available())
    except Exception:
        cuda = "unknown"
    return [("torch", version), ("torch-cuda", cuda)]


def probe_facts(
    *,
    smi_runner: SmiRunner = _run_nvidia_smi,
    torch_importer: Importer = importlib.import_module,
) -> list[tuple[str, str]]:
    """Gather ordered, torch-free environment facts as ``(key, value)`` pairs.

    Always reported: ``os``, ``arch``, ``gpu``, ``torch``, ``engine-dir``,
    ``home``, ``home-source``. When a GPU is visible and parseable, also
    ``driver``, ``driver-cuda`` (the driver's CUDA ceiling), and
    ``gpu-compute-cap`` (the ``sm_`` generation input to the wheel choice).
    When torch imports, also ``torch-cuda``. Every ``nvidia-smi`` failure
    degrades to a reported fact (``gpu: none`` when absent,
    ``gpu: unavailable`` on error/garbage) — probe never raises and never
    imports torch eagerly. Home facts come from
    :func:`stockroom.warehouse.resolve_home` (no mkdir).
    """
    home, home_source = resolve_home()
    return [
        ("os", platform.system()),
        ("arch", platform.machine()),
        *_gpu_facts(smi_runner),
        *_torch_facts(torch_importer),
        ("engine-dir", str(default_app_dir())),
        ("home", str(home)),
        ("home-source", home_source),
    ]


def format_facts(facts: list[tuple[str, str]]) -> str:
    """Render fact pairs as aligned ``key: value`` lines."""
    width = max(len(key) for key, _ in facts) + 1
    return "\n".join(f"{key + ':':<{width}} {value}" for key, value in facts)


def run_smoke(
    *,
    torch_importer: Importer = importlib.import_module,
    encoder_factory: Callable[[], Encoder] = BgeEncoder,
) -> int:
    """Verify the provisioned torch + encoder path; return an exit code.

    Happy path (exit 0): print ``torch: <version>``, ``cuda: <bool>``, encode
    one string through ``encoder_factory`` (production default:
    :class:`BgeEncoder`), check the vector is ``EMBED_DIM`` wide, and print
    an ``ok`` summary. Every failure prints exactly one stderr line carrying
    the next action (the errmsg ratchet) and returns 1:

    * torch not importable → names the engine environment (``APP_DIR``)
      and either ``stockroom shim ensure-env`` when a usable hashed freeze
      exists under stockroom home, or the literal
      ``uv pip install torch --no-config --index …`` command when it does
      not.
    * encoder construction/encode raises → names the exception and the
      re-pick remedy (re-run ``sr-initialize``, choose a different index).
    * wrong-width vector → broken setup, same re-pick remedy.
    """
    app_dir = default_app_dir()

    def fail(diagnosis: str, remedy: str) -> int:
        print(f"stockroom doctor: {diagnosis} — {remedy}", file=sys.stderr)
        return 1

    repick = (
        "re-run sr-initialize and pick a different torch wheel index "
        f"({_TORCH_INDEX_BASE}/<build>)"
    )

    try:
        torch = torch_importer("torch")
    except Exception:
        diagnosis = f"torch is not installed in the engine environment at {app_dir}"
        if read_freeze_path() is not None:
            return fail(
                diagnosis,
                "restore it with `stockroom shim ensure-env` "
                "(or re-run sr-initialize to re-pick a wheel)",
            )
        # --directory (not --project): uv pip discovers the venv from the
        # working directory, so --project alone fails with "No virtual
        # environment found" (verified live).
        return fail(
            diagnosis,
            "provision it there with "
            f"`uv pip install torch --no-config --index {_TORCH_INDEX_BASE}/<build> "
            f"--directory {app_dir}` (or re-run sr-initialize)",
        )

    print(f"torch: {torch.__version__}")
    print(f"cuda.is_available(): {torch.cuda.is_available()}")

    try:
        encoder = encoder_factory()
        vectors = encoder.encode(["stockroom doctor smoke test"])
    except Exception as exc:
        return fail(f"encoder check failed ({exc.__class__.__name__}: {exc})", repick)

    if len(vectors) != 1 or len(vectors[0]) != EMBED_DIM:
        got = len(vectors[0]) if vectors else 0
        return fail(
            f"encoder produced a {got}-dim vector (expected {EMBED_DIM})", repick
        )

    print(f"ok: encoded one string to a {EMBED_DIM}-dim vector")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``python -m stockroom.doctor`` parser (flat, like shim)."""
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.doctor",
        description=(
            "Read-only environment diagnostics. probe: report torch-free "
            "environment facts (OS, arch, GPU, driver, torch state); smoke: "
            "verify the provisioned torch + encoder path, failing loudly."
        ),
    )
    parser.add_argument(
        "action",
        choices=("probe", "smoke"),
        help="probe: print environment facts; smoke: verify torch + encoder",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m stockroom.doctor {probe|smoke}``.

    ``probe`` prints the fact lines and exits 0 (facts are never errors);
    ``smoke`` returns :func:`run_smoke`'s exit code.
    """
    args = _build_parser().parse_args(argv)
    if args.action == "probe":
        print(format_facts(probe_facts()))
        return 0
    return run_smoke()


if __name__ == "__main__":
    raise SystemExit(main())
