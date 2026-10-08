"""Delete all memories - run it to rehearse the demo from a clean state.

VectorAI DB deletes are unreliable in this version: deleted points can
reappear from the write-ahead log. So instead of deleting points, we
wipe the database storage and restart the container.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path
from uuid import uuid4

DATA_DIR = Path(__file__).resolve().parent / "local_data"
RESET_MARKER = Path(__file__).resolve().parent / ".memory-reset"

parser = argparse.ArgumentParser(description="Delete all collections in this repo's local VectorAI database.")
parser.add_argument("--container", default="vectorai", help="Docker container name (default: vectorai)")
parser.add_argument("--dry-run", action="store_true", help="Verify the container and storage path without deleting anything")
args = parser.parse_args()
inspection = subprocess.run(["docker", "inspect", args.container], capture_output=True, text=True)
if inspection.returncode:
    parser.exit(1, f"Cannot inspect container {args.container!r}. Pass its name with --container.\n{inspection.stderr}")
mounts = json.loads(inspection.stdout)[0].get("Mounts", [])
if not any(
    mount.get("Type") == "bind"
    and mount.get("Destination") == "/var/lib/actian-vectorai"
    and Path(mount["Source"]).resolve() == DATA_DIR.resolve()
    for mount in mounts
):
    parser.exit(1, f"Refusing reset: container must bind {DATA_DIR} to /var/lib/actian-vectorai.\n")
if args.dry_run:
    print(f"Would delete all database collections in {DATA_DIR} and restart {args.container}.")
    raise SystemExit(0)

subprocess.run(["docker", "stop", args.container], capture_output=True, check=True)
subprocess.run(
    [
        "docker", "run", "--rm",
        "-v", f"{DATA_DIR}:/data",
        "busybox",
        "sh", "-c", "rm -rf /data/* /data/.[!.]*",
    ],
    check=True,
)
# Notify running backends to drop histories that still contain old preferences.
RESET_MARKER.write_text(str(uuid4()), encoding="utf-8")
subprocess.run(["docker", "start", args.container], capture_output=True, check=True)
time.sleep(8.0)

print("All memories deleted. Backend conversation histories will reset on the next request.")
