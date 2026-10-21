"""Process-local compatibility launcher; never edits installed packages.

threadpoolctl 3.7.0 snapshot paths can be lossy in this Windows/Unicode workspace.
Discard snapshot *path strings* while preserving loaded module handles, so the
library's existing GetModuleFileNameW/GetModuleFileNameExW resolver obtains the
correct Unicode path. All statistical protocol files remain sealed unchanged.
"""
import argparse
import os
from pathlib import Path

import threadpoolctl


def handles_only(modules):
    return None if modules is None else [(handle, "") for handle, _ in modules]


def install_adapter():
    if os.name != "nt":
        return "not needed on this platform"
    if threadpoolctl.__version__ != "3.7.0":
        raise RuntimeError("This narrow compatibility adapter requires threadpoolctl 3.7.0")
    original = threadpoolctl.ThreadpoolController._snapshot_loaded_modules

    def unicode_resolved_snapshot(self, kernel32):
        return handles_only(original(self, kernel32))

    threadpoolctl.ThreadpoolController._snapshot_loaded_modules = unicode_resolved_snapshot
    return "snapshot handles retained; paths resolved by existing Windows wide-character APIs"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "train", "evaluate", "verify"])
    parser.add_argument("--run-dir", default="data/experiments/classification/task06b-v1-final")
    args = parser.parse_args()
    description = install_adapter()
    import run_classification_experiment as experiment

    run = (experiment.ROOT / args.run_dir).resolve()
    if not run.is_relative_to(experiment.RUN_BASE.resolve()) or run == experiment.RUN_BASE.resolve():
        parser.error("Run directory must be a child of ignored data/experiments/classification/")
    if args.phase in {"train", "evaluate", "verify"}:
        experiment.verify_lock(run)
        adapter_sha = experiment.file_sha(Path(__file__))
        library_sha = experiment.file_sha(Path(threadpoolctl.__file__))
        receipt_path = run / "runtime-adapter.json"
        if receipt_path.exists():
            previous = experiment.read_json(receipt_path)
            if previous["adapter_sha256"] != adapter_sha or previous["threadpoolctl_source_sha256"] != library_sha or previous["split_lock_sha256"] != experiment.file_sha(run / "split-lock.json"):
                raise ValueError("Compatibility receipt no longer matches the sealed run")
        elif args.phase == "train":
            with threadpoolctl.threadpool_limits(limits=experiment.config()["thread_limit"]):
                info = threadpoolctl.threadpool_info()
                if any(item["num_threads"] != 1 for item in info):
                    raise ValueError("Single-thread limit not effective")
            receipt = {"recorded_before_first_fit_at_utc": experiment.now(), "description": description,
                       "adapter_sha256": adapter_sha, "threadpoolctl_source_sha256": library_sha,
                       "threadpoolctl_version": threadpoolctl.__version__,
                       "split_lock_sha256": experiment.file_sha(run / "split-lock.json"),
                       "threadpools_during_limit": [{"internal_api": item["internal_api"], "num_threads": item["num_threads"]} for item in info],
                       "installed_packages_modified": False, "config_or_split_modified": False}
            experiment.write_json(receipt_path, receipt, exclusive=True)
            experiment.write_json(experiment.SHARE / "classification-experiment-runtime.json", receipt)
            experiment.event(run, "runtime_compatibility_recorded_before_fit", adapter_sha256=adapter_sha)
        else:
            raise ValueError("Missing pre-fit runtime compatibility receipt")
    {"prepare": experiment.prepare, "train": experiment.train,
     "evaluate": experiment.evaluate, "verify": experiment.verify}[args.phase](run)


if __name__ == "__main__":
    main()
