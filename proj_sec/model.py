from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from .common import MODEL_ID, MODEL_REVISION, external_environment, write_json


def model_python(explicit: str | None = None) -> str:
    if explicit:
        # Keep the venv launcher path: resolving its symlink can select the
        # base interpreter and lose the model packages installed in the venv.
        return str(Path(explicit).expanduser().absolute())
    if getattr(sys, "frozen", False):
        environment = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
        if not environment:
            raise ValueError("Activate the model Python/Conda environment or provide --model-python")
        return str(Path(environment) / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    return sys.executable


class GemmaGenerator:
    def __init__(self, output_dir, *, python=None, device="auto", model_path=None,
                 max_new_tokens=1024, timeout=1800, dtype="auto"):
        if dtype not in ("auto", "float32", "float16", "bfloat16"):
            raise ValueError("Unsupported model dtype")
        self.dtype = dtype
        self.python = model_python(python)
        self.output_dir = Path(output_dir)
        self.device, self.model_path = device, model_path or MODEL_ID
        self.max_new_tokens, self.timeout = max_new_tokens, timeout
        self.revision = MODEL_REVISION if self.model_path == MODEL_ID else "local"
        self.identity = f"{MODEL_ID}|{self.model_path}|{self.revision}|{device}|greedy|seed42|tokens{max_new_tokens}|dtype{dtype}|schema2"
        self.process = self.log = None
        self.responses = queue.Queue()

    def __enter__(self):
        return self

    def _start(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log = (self.output_dir / "gemma-worker.log").open("a", encoding="utf-8")
        worker = Path(__file__).with_name("workers") / "gemma_worker.py"
        self.process = subprocess.Popen(
            [self.python, "-u", str(worker), self.model_path, self.device, self.revision, self.dtype],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding="utf-8", bufsize=1, env=external_environment(),
        )
        def read_responses():
            for line in self.process.stdout:
                self.responses.put(line)
            self.responses.put(None)
        threading.Thread(target=read_responses, daemon=True).start()

    def __call__(self, prompt):
        return self._request(prompt)

    def select_ids(self, prompt, candidate_count, *, allow_empty=False):
        if (isinstance(candidate_count, bool) or not isinstance(candidate_count, int)
                or not 1 <= candidate_count <= 12):
            raise ValueError("Selection candidate count must be between 1 and 12")
        if not isinstance(allow_empty, bool):
            raise ValueError("allow_empty must be a boolean")
        return self._request(prompt, selection_constraint={"kind": "source-id-trie-v1",
                             "candidate_count": candidate_count, "allow_empty": allow_empty})

    def _request(self, prompt, *, selection_constraint=None):
        if self.process is None:
            self._start()
        request = {"prompt": prompt, "max_new_tokens": self.max_new_tokens}
        if selection_constraint is not None:
            request["selection_constraint"] = selection_constraint
        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            line = self.responses.get(timeout=self.timeout)
        except (BrokenPipeError, queue.Empty) as exc:
            raise RuntimeError("Gemma worker failed or timed out; inspect gemma-worker.log") from exc
        if line is None:
            raise RuntimeError("Gemma worker exited; inspect gemma-worker.log for installation/access errors")
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(f"Gemma extraction failed: {response['error']}")
        if (selection_constraint is not None
                and response.get("decoding_constraint") != selection_constraint["kind"]):
            raise RuntimeError("Gemma worker did not confirm the required source-ID decoding constraint")
        write_json(self.output_dir / "model-runtime.json", {
            "model": MODEL_ID, "revision": response.get("revision"), "device": response.get("device"),
            "identity": self.identity, "dtype": response.get("dtype"),
            "decoding_constraint": response.get("decoding_constraint", "unconstrained"),
        })
        return response["output"]

    def __exit__(self, *args):
        if self.process is not None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process.stdout.close()
        if self.log is not None:
            self.log.close()
