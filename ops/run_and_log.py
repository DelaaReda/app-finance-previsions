import sys
import subprocess
import getpass
from src.ops.logging_conf import log_activity


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m ops.run_and_log <cmd> [args...]")
        sys.exit(1)
    cmd = sys.argv[1:]
    user = getpass.getuser()
    log_activity("cmd", {"user": user, "cmd": cmd})
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate()
    print(out)
    log_activity("cmd_result", {"user": user, "cmd": cmd, "rc": p.returncode, "out_tail": out[-2000:]})
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()

