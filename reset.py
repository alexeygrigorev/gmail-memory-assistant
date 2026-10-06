"""Delete all memories - run it to rehearse the demo from a clean state.

VectorAI DB deletes are unreliable in this version: deleted points can
reappear from the write-ahead log. So instead of deleting points, we
wipe the database storage and restart the container.
"""

import subprocess
import time
from pathlib import Path

DATA_DIR = Path.cwd() / "local_data"

subprocess.run(["docker", "stop", "vectorai"], capture_output=True, check=True)
subprocess.run(
    [
        "docker", "run", "--rm",
        "-v", f"{DATA_DIR}:/data",
        "busybox",
        "sh", "-c", "rm -rf /data/* /data/.[!.]*",
    ],
    check=True,
)
subprocess.run(["docker", "start", "vectorai"], capture_output=True, check=True)
time.sleep(8.0)

print("All memories deleted.")
