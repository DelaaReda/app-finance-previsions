import shutil
import datetime
from pathlib import Path


OUT = Path("artifacts")
OUT.mkdir(exist_ok=True, parents=True)


def main():
    ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    name = f"ui_artifacts_{ts}"
    tmp = OUT / name
    tmp.mkdir(parents=True, exist_ok=True)

    for p in ["artifacts/ui_health", "data/reports", "logs", "data/llm_summary"]:
        q = Path(p)
        if q.exists():
            shutil.copytree(q, tmp / q.name, dirs_exist_ok=True)

    shutil.make_archive(str(OUT / name), "zip", tmp)
    print(f"[pack] -> {OUT}/{name}.zip")


if __name__ == "__main__":
    main()

