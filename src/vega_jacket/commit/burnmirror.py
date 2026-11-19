"""burnmirror.py - hash-chained side-car mirror of every burned nonce.
  Written guarantee it implements: a restart is not a replay window -- INCLUDING
  when the DAG store itself is reset, moved or recreated between runs. The burn
  lives in TWO independent places (DAG + mirror); erasing one does not erase the
  record. If the DAG and the mirror disagree, that IS a tamper alarm.
  - each line: nonce_sha256 + action + sha256(line + prev_line_chain_hash)
  - append-only, fsync on write; deletion of the DAG file cannot clear it
  - deleting the mirror itself fails CLOSED: any burns expected on the DAG
    but missing from the mirror are treated as tamper, not replay opportunity.
Pure stdlib. Raises BurnMirrorError on any integrity failure."""
import hashlib, json, os, time


class BurnMirrorError(Exception):
    pass


def _chain_hash(payload: str, prev_chain: str) -> str:
    return hashlib.sha256((payload + prev_chain).encode("utf-8")).hexdigest()


class BurnMirror:
    def __init__(self, path: str):
        self.path = path
        self.chain = ""
        self.lines = 0

    def load(self) -> set:
        """Returns the set of burned nonce hashes; verifies the chain line by line.
        Idempotent: resets chain position so repeated calls on one instance re-verify from line 1."""
        burned = set()
        self.chain, self.lines = "", 0
        if not os.path.exists(self.path):
            return burned  # empty mirror is valid ONLY if the DAG shows no burns either (checked by Commit)
        with open(self.path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                rec = json.loads(line)
                expect = rec.pop("chain", None)
                if expect != _chain_hash(json.dumps(rec, sort_keys=True), self.chain):
                    raise BurnMirrorError(f"burn mirror chain broken at line {self.lines + 1} - MIRROR TAMPERED")
                burned.add(rec["nonce_sha256"])
                self.lines += 1
                self.chain = expect
        return burned

    def append(self, nonce_sha256: str, action: str) -> None:
        rec = {"nonce_sha256": nonce_sha256, "action": action, "ts": time.time()}
        rec["chain"] = _chain_hash(json.dumps(rec, sort_keys=True), self.chain)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.lines += 1
        self.chain = rec["chain"]
