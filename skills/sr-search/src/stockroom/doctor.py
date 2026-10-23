"""Read-only environment diagnostics (``python -m stockroom.doctor``).

The Phase-3 m3 diagnostic surface behind ``sr-initialize``. Two actions,
both constitutionally read-only (they never install, sync, or write):

* ``probe`` — torch-free environment facts: OS/arch (``platform``), GPU
  name / driver / driver-CUDA ceiling / compute capability (``nvidia-smi``
  in its stable ``--query-gpu=`` CSV mode; absence or failure is a
  *reported fact*, never an error), torch import state, the engine
  directory, the resolved warehouse home / how it was chosen
  (``home`` / ``home-source``), and warehouse storage (file size, block
  use, a reclaimable estimate, the storage format, free disk, and an
  existing swap backup). Facts only — the torch-wheel recommendation
  mapping is judgment and lives in the ``sr-initialize`` skill prose.
  Storage facts never create or migrate a warehouse.
* ``smoke`` — the loud-failing torch/encoder verification: prints
  ``torch.__version__`` and ``torch.cuda.is_available()``, then encodes one
  string through the production :class:`stockroom.embed.BgeEncoder` path
  and checks the vector width. Exit 0 with an ``ok`` summary, or exit 1
  with exactly one stderr line that always carries the *next action*
  (the errmsg ratchet: torch-missing names the engine environment and
  either ``stockroom shim ensure-env`` when a usable freeze exists or
  ``sr-initialize`` when it does not; encode failures name
  ``sr-initialize``). ``smoke`` never installs.

Testability follows the engine-wide injection precedent: ``probe_facts``
takes an injectable ``nvidia-smi`` runner and torch importer (so it is
fully covered torch-free), ``run_smoke`` takes an injectable torch importer
and encoder factory (the real-model path is the one
``importorskip("torch")``-gated test).

Design record: ``memory-bank/active/creative/creative-onboarding-logic-surface.md``.
"""

import argparse
import fcntl
import importlib
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import duckdb

from stockroom.embed import (
    EMBED_DIM,
    BgeEncoder,
    Encoder,
    encoder_load_remedy,
    missing_torch_remedy,
)
from stockroom.migrate import current_version
from stockroom.shim import default_app_dir
from stockroom.warehouse import (
    LOCK_FILENAME,
    WAREHOUSE_FILENAME,
    _latest_version,
    resolve_home,
)

#: An injectable runner for ``nvidia-smi``: takes the argument list (after
#: the executable) and returns stdout text, raising on any failure
#: (``FileNotFoundError`` when the binary is absent).
SmiRunner = Callable[[list[str]], str]

#: An injectable importer with the :func:`importlib.import_module` signature.
Importer = Callable[[str], object]

#: An injectable ``duckdb.connect``. Tests pass a substitute; the default
#: opens the warehouse file read-only.
Connect = Callable[..., duckdb.DuckDBPyConnection]

#: Swap backup name milestone 6 writes and this report reads.
#: ``warehouse.issue147-`` is the stockroom backup prefix, so a user's own
#: ``warehouse.duckdb.bak`` is never reported as this file.
SWAP_BACKUP_FILENAME = "warehouse.issue147-swap.duckdb"


def live_bytes(con: duckdb.DuckDBPyConnection) -> int:
    """Return the live-size estimate for an open warehouse, in bytes.

    The estimate is the number of distinct persistent block ids from
    ``pragma_storage_info``, times ``block_size`` from
    ``pragma_database_size``. Block ids below 0 are dropped. Each base
    table in ``main`` contributes its ids; views are skipped. A non-empty
    ``additional_block_ids`` list is part of the same union.
    """
    block_size = con.execute(
        "SELECT block_size FROM pragma_database_size() "
        "WHERE database_name = current_database()"
    ).fetchone()[0]
    views = {
        name
        for (name,) in con.execute(
            "SELECT view_name FROM duckdb_views() "
            "WHERE database_name = current_database() AND schema_name = 'main'"
        ).fetchall()
    }
    tables = [
        name
        for (name,) in con.execute(
            "SELECT table_name FROM duckdb_tables() "
            "WHERE database_name = current_database() AND schema_name = 'main'"
        ).fetchall()
        if name not in views
    ]
    ids: set[int] = set()
    for name in tables:
        literal = "'" + name.replace("'", "''") + "'"
        rows = con.execute(
            "SELECT block_id, additional_block_ids "
            f"FROM pragma_storage_info({literal}) WHERE persistent"
        ).fetchall()
        for block_id, extra in rows:
            if block_id is not None and int(block_id) >= 0:
                ids.add(int(block_id))
            if extra:
                for extra_id in extra:
                    if extra_id is not None and int(extra_id) >= 0:
                        ids.add(int(extra_id))
    return len(ids) * int(block_size)


def _disk_free(path: Path) -> int:
    """Free bytes at ``path``, or at the nearest existing parent."""
    anchor = path
    while not anchor.exists():
        parent = anchor.parent
        if parent == anchor:
            break
        anchor = parent
    return int(shutil.disk_usage(anchor).free)


def _backup_facts(home: Path) -> list[tuple[str, str]]:
    """Report the swap backup file, or ``backup: absent``."""
    backup = home / SWAP_BACKUP_FILENAME
    if not backup.is_file():
        return [("backup", "absent")]
    return [("backup", str(backup)), ("backup-bytes", str(backup.stat().st_size))]


def _writer_lock_busy(lock: Path) -> bool:
    """True when ``lock`` exists and a non-blocking exclusive flock fails.

    Opens with no ``O_CREAT``. A successful acquire is released before
    returning, so the caller does not keep the writer lock.
    """
    if not lock.is_file():
        return False
    try:
        fd = os.open(lock, os.O_RDWR)
    except OSError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def storage_facts(
    home: Path, *, connect: Connect = duckdb.connect
) -> list[tuple[str, str]]:
    """Return read-only storage facts for the warehouse under ``home``.

    Does not create the home, the warehouse file, or the lock file, and
    does not migrate. A missing home or a missing warehouse file is
    ``warehouse: absent`` and ``connect`` is not called. A held writer
    flock is ``warehouse: busy`` and ``connect`` is not called. A connect
    or pragma failure on an existing file is ``warehouse: unavailable``.
    ``disk-free`` is always present. The swap backup is reported only
    when :data:`SWAP_BACKUP_FILENAME` is a file in ``home``.

    ``connect`` is ``duckdb.connect`` unless a test injects a substitute.
    """
    disk_free = ("disk-free", str(_disk_free(home)))
    backup = _backup_facts(home)
    warehouse_file = home / WAREHOUSE_FILENAME
    if not home.is_dir() or not warehouse_file.is_file():
        return [("warehouse", "absent"), disk_free, *backup]

    size = warehouse_file.stat().st_size
    stat_facts = [("warehouse-bytes", str(size)), disk_free, *backup]
    if _writer_lock_busy(home / LOCK_FILENAME):
        return [("warehouse", "busy"), *stat_facts]

    try:
        con = connect(str(warehouse_file), read_only=True)
        try:
            used, free = con.execute(
                "SELECT used_blocks, free_blocks FROM pragma_database_size() "
                "WHERE database_name = current_database()"
            ).fetchone()
            tags = con.execute(
                "SELECT tags FROM duckdb_databases() "
                "WHERE database_name = current_database()"
            ).fetchone()[0]
            storage = tags["storage_version"]
            if current_version(con) < _latest_version():
                # The file is behind the schema head. Report it; do not migrate.
                pass
            reclaimable = size - live_bytes(con)
        finally:
            con.close()
    except Exception:
        return [("warehouse", "unavailable"), *stat_facts]

    return [
        ("warehouse", str(warehouse_file)),
        ("warehouse-bytes", str(size)),
        ("blocks-used", str(int(used))),
        ("blocks-free", str(int(free))),
        ("reclaimable-bytes", str(reclaimable)),
        ("storage", str(storage)),
        disk_free,
        *backup,
    ]


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
    ``home``, ``home-source``, plus the storage facts from
    :func:`storage_facts` (always ``disk-free``; ``warehouse`` is
    ``absent``, ``busy``, ``unavailable``, or the warehouse path). When a
    GPU is visible and parseable, also ``driver``, ``driver-cuda`` (the
    driver's CUDA ceiling), and ``gpu-compute-cap`` (the ``sm_`` generation
    input to the wheel choice). When torch imports, also ``torch-cuda``.
    Every ``nvidia-smi`` failure degrades to a reported fact (``gpu: none``
    when absent, ``gpu: unavailable`` on error/garbage) — probe never
    raises and never imports torch eagerly. Home facts come from
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
        *storage_facts(home),
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
      exists under stockroom home, or ``sr-initialize`` when it does not.
      ``smoke`` reports; it does not install.
    * encoder construction/encode raises → names the exception and
      ``sr-initialize``.
    * wrong-width vector → broken setup, same ``sr-initialize`` remedy.
    """
    app_dir = default_app_dir()

    def fail(diagnosis: str, remedy: str) -> int:
        print(f"stockroom doctor: {diagnosis} — {remedy}", file=sys.stderr)
        return 1

    try:
        torch = torch_importer("torch")
    except Exception:
        diagnosis = f"torch is not installed in the engine environment at {app_dir}"
        return fail(diagnosis, missing_torch_remedy())

    print(f"torch: {torch.__version__}")
    print(f"cuda.is_available(): {torch.cuda.is_available()}")

    try:
        encoder = encoder_factory()
        vectors = encoder.encode(["stockroom doctor smoke test"])
    except Exception as exc:
        return fail(
            f"encoder check failed ({exc.__class__.__name__}: {exc})",
            encoder_load_remedy(),
        )

    if len(vectors) != 1 or len(vectors[0]) != EMBED_DIM:
        got = len(vectors[0]) if vectors else 0
        return fail(
            f"encoder produced a {got}-dim vector (expected {EMBED_DIM})",
            encoder_load_remedy(),
        )

    print(f"ok: encoded one string to a {EMBED_DIM}-dim vector")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``python -m stockroom.doctor`` parser (flat, like shim)."""
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.doctor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Read-only environment diagnostics.\n"
            "probe: report torch-free environment facts (OS, arch, GPU, driver,\n"
            "torch state) and warehouse storage facts: file size, used blocks,\n"
            "free blocks, the reclaimable estimate, the storage format, free disk,\n"
            "and backup.\n"
            "smoke: verify the provisioned torch + encoder path, failing loudly."
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
