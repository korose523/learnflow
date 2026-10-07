import argparse
import json
import hashlib
from pathlib import Path
from .core import audit


def main():
    parser = argparse.ArgumentParser(description="Read-only intervention contract audit")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = args.manifest.read_bytes()
        result = audit(json.loads(raw), args.source_root)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    result["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{result['mechanisms']} declarations; {len(result['findings'])} findings; output {args.output}")
    return 0


if __name__ == "__main__":
    main()
