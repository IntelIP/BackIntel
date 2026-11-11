"""Operator commands for quality checks and the supervised improvement workflow."""

from __future__ import annotations

import json
from pathlib import Path

from backintel.settings import repo_root


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep previous comparison/proposal evidence instead of silently replacing it.
    with path.open("x") as handle:
        handle.write(json.dumps(value, indent=2, default=str) + "\n")
    print(path)


def _budget(args):
    from backintel.bench.usage import RunBudget

    return RunBudget(args.max_cost_usd, args.max_calls, args.reservation_usd)


def cmd_quality(args, settings):
    from backintel.bench.quality import write_quality_report

    if args.output.exists():
        raise ValueError("Choose a new output path to preserve the previous quality report")
    report = write_quality_report(settings, args.output)
    print(json.dumps(report, indent=2, default=str))


def cmd_acceptance(args, settings):
    from backintel.bench.acceptance import build_acceptance, verify_acceptance_data

    if args.action == "run" and args.max_cost_usd is None:
        raise ValueError("Paid acceptance runs require an explicitly authorized --max-cost-usd")
    if args.trials < 1:
        raise ValueError("trials must be positive")
    suite = build_acceptance(settings, split=args.split)
    if args.action == "build":
        print(
            json.dumps(
                {
                    "dataset": suite.dataset,
                    "cases": len(suite.scenarios),
                    "data_hash": suite.data_hash,
                    "reference_hash": suite.reference_hash,
                    "manifest": str(suite.manifest_path),
                },
                indent=2,
            )
        )
        return
    from backintel.bench.run import Harness, run_langsmith, run_local, select

    budget = _budget(args)
    wanted = set(args.ids.split(",")) if args.ids else None
    scenarios = select(suite.scenarios, levels=None, ids=wanted, limit=None)
    if not scenarios or (wanted and wanted != {s.id for s in scenarios}):
        raise ValueError("Case IDs must name existing cases in the selected split")
    harness = Harness.build(
        settings,
        dataset=suite.dataset,
        store_id=scenarios[0].store,
        scenarios=suite.scenarios,
        data_version=suite.data_hash,
        budget=budget,
    )
    reports = []
    try:
        for trial in range(args.trials):
            if not verify_acceptance_data(suite, settings):
                raise ValueError("Acceptance data changed before the trial")
            harness.run_metadata["trial"] = trial
            if args.no_langsmith:
                from uuid import uuid4

                path = run_local(harness, scenarios, name=f"{suite.dataset}-trial{trial}-{uuid4().hex[:8]}")
                reports.append({"path": str(path)})
            else:
                reports.append(run_langsmith(harness, scenarios, max_concurrency=1))
            if not verify_acceptance_data(suite, settings):
                raise ValueError("Acceptance data changed during the trial; results cannot be accepted")
            if not budget.can_admit():
                break
    finally:
        harness.close()
    print(json.dumps({"experiments": reports, "budget": budget.report()}, indent=2))


def cmd_improve(args, settings):
    from backintel.bench.improvement import (
        ComparisonPolicy,
        apply_candidate,
        compare_records,
        propose_candidate,
        read_records,
        validate_runtime_paths,
    )

    if args.action == "compare":
        policy = ComparisonPolicy.from_document(json.loads(args.policy.read_text()))
        result = compare_records(read_records(args.baseline), read_records(args.candidate), policy)
        _write(args.output, result)
        print(result["verdict"])
        if result["verdict"] != "accept_for_review":
            raise SystemExit(1)
    elif args.action == "propose":
        if args.output.exists():
            raise ValueError("Proposal output already exists; choose a new evidence path")
        validate_runtime_paths(args.files)
        root = args.workspace.resolve()
        files = {}
        for name in args.files:
            path = root / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Editable source escapes the workspace")
            files[name] = path.read_text()
        budget = _budget(args)
        result = propose_candidate(
            files,
            args.brief.read_text(),
            model_id=settings.model,
            budget=budget,
        )
        result["budget"] = budget.report()
        _write(args.output, result)
        if result["status"] != "proposed":
            raise SystemExit(1)
    elif args.action == "apply":
        print(json.dumps(apply_candidate(json.loads(args.proposal.read_text()), args.workspace)))
    elif args.action == "review":
        from backintel.bench.calibration import write_review_packet

        print(json.dumps(write_review_packet(read_records(args.records), args.output), indent=2))
    elif args.action == "calibrate":
        from backintel.bench.calibration import assess_calibration

        result = assess_calibration(
            json.loads(args.packet.read_text()),
            json.loads(args.labels.read_text()),
            json.loads(args.judges.read_text()),
        )
        _write(args.output, result)
        if result["status"] != "reviewed":
            raise SystemExit(1)


def _budget_arguments(parser, *, required=True):
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        required=required,
        help="explicitly authorized allowance for this invocation",
    )
    parser.add_argument("--max-calls", type=int, default=500)
    parser.add_argument(
        "--reservation-usd",
        type=float,
        default=0.05,
        help="reserve before each model call; stop if actual cost exceeds reservation",
    )


def add_commands(sub):
    quality = sub.add_parser("quality", help="profile benchmark data and independently check references")
    quality.add_argument("--output", type=Path, required=True)
    quality.set_defaults(func=cmd_quality)

    acceptance = sub.add_parser("acceptance", help="build or evaluate development/reserved contrast cases")
    acceptance.add_argument("action", choices=("build", "run"))
    acceptance.add_argument("--split", choices=("development", "acceptance"), default="development")
    acceptance.add_argument("--ids", help="comma-separated exact case IDs")
    acceptance.add_argument("--trials", type=int, default=1)
    acceptance.add_argument("--no-langsmith", action="store_true")
    _budget_arguments(acceptance, required=False)
    acceptance.set_defaults(func=cmd_acceptance)

    improve = sub.add_parser("improve", help="propose, evaluate and review a supervised candidate")
    actions = improve.add_subparsers(dest="action", required=True)
    compare = actions.add_parser("compare")
    for name in ("baseline", "candidate", "policy", "output"):
        compare.add_argument(f"--{name}", type=Path, required=True)
    propose = actions.add_parser("propose")
    propose.add_argument("--workspace", type=Path, default=repo_root())
    propose.add_argument("--files", nargs="+", required=True)
    for name in ("brief", "output"):
        propose.add_argument(f"--{name}", type=Path, required=True)
    _budget_arguments(propose)
    apply = actions.add_parser("apply")
    apply.add_argument("--proposal", type=Path, required=True)
    apply.add_argument("--workspace", type=Path, required=True)
    review = actions.add_parser("review")
    for name in ("records", "output"):
        review.add_argument(f"--{name}", type=Path, required=True)
    calibrate = actions.add_parser("calibrate")
    for name in ("packet", "labels", "judges", "output"):
        calibrate.add_argument(f"--{name}", type=Path, required=True)
    improve.set_defaults(func=cmd_improve)
