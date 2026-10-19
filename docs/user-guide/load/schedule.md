
# Scheduling

Freshness is a nightly `stockroom ingest && stockroom embed` (incremental, not `--full`) on the platform scheduler — cron on Linux/WSL, launchd on macOS. Native Windows is not supported; use WSL. Output goes to `$STOCKROOM_HOME/logs/nightly.log`.

`sr-initialize` asks before installing the job. You can change the time, skip scheduling entirely, or manage it later:

```bash
stockroom schedule status
stockroom schedule install
stockroom schedule install --time 01:15
stockroom schedule remove
```

`install` is idempotent — it replaces Stockroom's own entry, never duplicates it, and on cron it only touches a comment-delimited block. If `status` warns that the cron daemon is not running, the entry is written but will not fire until you start the daemon.

cron and launchd do not load your shell profile, so the entry carries the stockroom home it was installed for (`STOCKROOM_HOME`); `status` shows it as `entry home:`. `status` also says `up-to-date: no` when the entry differs from what `install` writes now, for example after a Stockroom update changed the entry, or after you changed `STOCKROOM_HOME` or `XDG_DATA_HOME`. Then run `stockroom schedule install --time HH:MM` again with your own time; without `--time`, `install` uses 03:30.

The optional schedule entry is also called out under [Installed layout](../installed-layout.md). Session-start hooks never ingest or embed — they only heal the shim and launch the dashboard.