"""Command line: data, oracle, ask, bench, chatgpt, sandbox. Run under Doppler for credentials."""

from __future__ import annotations

import argparse
import json
import sys

from backintel.settings import Settings

DATASETS = ("online_retail_ii", "olist", "tpch_sf1", "tpch_sf0_1")


def _datasets(name: str) -> tuple[str, ...]:
    return ("online_retail_ii", "olist") if name == "all" else (name,)


def cmd_data(args, settings):
    from backintel.bench.build_stores import build_sqlite
    from backintel.bench.datasets import DATASETS as SPECS
    from backintel.bench.datasets import build_canonical, download

    for name in _datasets(args.dataset):
        if args.action == "download":
            print(name, download(SPECS[name], settings, force=args.force))
        else:
            manifest = build_canonical(name, settings, force=args.force)
            print(name, "canonical tables:", manifest["tables"])
            print(name, "sqlite:", build_sqlite(name, settings, force=args.force))


def cmd_split(args, settings):
    from backintel.bench.build_stores import build_postgres, build_sqlite
    from backintel.bench.datasets import SPLITS

    for name, (_base, tables) in SPLITS.items():
        if args.split not in ("all", name):
            continue
        print(name, "tables:", tables)
        if name == "olist_orders":
            print(" ", build_postgres(name, settings, force=args.force))
        else:
            print(" ", build_sqlite(name, settings, force=args.force))


def cmd_tpch(args, settings):
    import json as _json
    from datetime import UTC, datetime

    from backintel.bench.oracle.tpch import generate

    name = f"tpch_sf{args.sf:g}".replace(".", "_")
    out = settings.canonical_dir / name
    counts = generate(out, scale_factor=args.sf)
    (out / "MANIFEST.json").write_text(
        _json.dumps(
            {
                "name": name,
                "title": f"TPC-H scale factor {args.sf:g} (DuckDB tpch extension)",
                "licence": "TPC-H generated test data; see https://www.tpc.org/tpch/",
                "archive_sha256": "generated",
                "tables": counts,
                "built_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
    )
    print(name, counts)


def cmd_replay(args, settings):
    from backintel.bench.build_stores import build_replay_snapshots

    for path in build_replay_snapshots(settings, force=args.force):
        print(path)


def cmd_stores(args, settings):
    from backintel.stores import services

    if args.action == "build":
        for dataset in _datasets(args.dataset):
            services.build(args.kind, dataset, settings, force=args.force)
    elif args.action == "up":
        services.up(args.kind, settings)
    else:
        services.compose(args.kind, "stop")


def cmd_oracle(args, settings):
    from backintel.bench.oracle import build_answers

    for name in _datasets(args.dataset):
        scenarios = build_answers(name, settings)
        print(f"{name}: {len(scenarios)} scenarios, {sum(not s.answerable for s in scenarios)} unanswerable")
        for s in scenarios:
            print(f"  {s.id} L{s.level} {s.answer_type}: {str(s.expected)[:80]}")


def cmd_ask(args, settings):
    from backintel.bench.run import Harness

    harness = Harness.build(
        settings,
        dataset="ad-hoc",
        store_id=args.store,
        model_id=args.model,
        judge=False,
        scenarios=[],  # Ad-hoc stores need no evaluator-owned reference dataset.
    )
    try:
        print(json.dumps(harness.answer(args.question), indent=2, default=str))
    finally:
        harness.close()


def cmd_bench(args, settings):
    from backintel.bench.run import Harness, rescore, run_langsmith, run_local, select, sync_dataset
    from backintel.bench.scorecard import build_scorecard

    if args.action == "sync":
        print(json.dumps(sync_dataset(args.dataset), indent=2))
        return
    if args.action == "scorecard":
        print(build_scorecard(experiments=args.experiments or None))
        return
    if args.action == "rescore":
        for experiment in args.experiments or []:
            print(rescore(experiment, settings, judge=not args.no_judge))
        print(build_scorecard())
        return
    levels = {int(x) for x in args.levels.split(",")} if args.levels else None
    ids = set(args.ids.split(",")) if args.ids else None
    harness = Harness.build(
        settings,
        dataset=args.dataset,
        store_id=args.store,
        model_id=args.model,
        judge=not args.no_judge,
    )
    try:
        scenarios = select(harness.scenarios.values(), levels=levels, ids=ids, limit=args.limit)
        print(
            f"{len(scenarios)} scenarios on {args.store} with {harness.model_id}; "
            f"sandbox={harness.sandbox.label}",
            flush=True,
        )
        if args.no_langsmith:
            print(run_local(harness, scenarios))
        else:
            print(json.dumps(run_langsmith(harness, scenarios, max_concurrency=args.concurrency), indent=2))
    finally:
        harness.close()
    print(build_scorecard())


def cmd_chatgpt(args, settings):
    from backintel.providers.chatgpt_plan import PlanCredentials, SignInRequired, sign_in

    credentials = PlanCredentials()
    if args.action == "status":
        print(json.dumps(credentials.status(), indent=2))
    elif args.action == "models":
        print(json.dumps(credentials.models(), indent=2))
    elif args.action == "logout":
        print(
            "revoked"
            if credentials.sign_out()
            else "signed out locally; revoke in ChatGPT settings if needed"
        )
    else:
        try:
            record = sign_in(
                credentials,
                announce=lambda m: print(m, flush=True),
                open_browser=lambda url: None if args.no_browser else __import__("webbrowser").open(url),
            )
        except SignInRequired as error:
            sys.exit(str(error))
        print(f"Signed in as {record.get('email')}; BackIntel model calls now use your ChatGPT plan.")


def cmd_sandbox(args, settings):
    from backintel.sandbox import PythonSandbox, describe_backend

    sandbox = PythonSandbox(settings.sandbox)
    print(json.dumps(describe_backend(sandbox)))
    result = sandbox.run(
        "import sys, polars, pandas\nprint(sys.version.split()[0], polars.__version__, pandas.__version__)\n"
        "import socket\n"
        "try:\n    socket.create_connection(('1.1.1.1', 80), timeout=3); print('network: reachable')\n"
        "except Exception as e:\n    print('network: blocked', type(e).__name__)",
        env={},
        mounts={},
    )
    print(json.dumps(result.to_dict(), indent=2))


def cmd_analyze(args, settings):
    import asyncio
    from pathlib import Path

    from backintel.analysis import AnalysisBrief, run_analysis
    from backintel.bench.usage import PlanRunBudget, RunBudget
    from backintel.models import build_model
    from backintel.stores import open_store

    if settings.sandbox != "smolvm":
        raise ValueError("The analysis specialist requires SmolVM; host subprocess mode is not allowed.")
    model_id = args.model or settings.analysis_model
    plan = model_id.startswith("chatgpt-plan/")
    if plan:
        if args.max_cost_usd is not None or args.reservation_usd is not None:
            raise ValueError("ChatGPT subscription usage uses call limits, not API dollar reservations.")
        budget = PlanRunBudget(args.max_model_calls)
    elif model_id.startswith("openrouter/"):
        if args.max_cost_usd is None or args.reservation_usd is None:
            raise ValueError("OpenRouter requires --max-cost-usd and --reservation-usd.")
        budget = RunBudget(args.max_cost_usd, args.max_model_calls, args.reservation_usd)
    else:
        raise ValueError("Analysis supports explicit openrouter/ or chatgpt-plan/ models.")
    brief = AnalysisBrief.model_validate_json(Path(args.brief).read_text())
    model = build_model(
        model_id,
        max_retries=0,
        reasoning_effort=args.reasoning,
        responses_api=args.responses_api,
        first_party_only=not plan,
        timeout_s=min(args.timeout, 300),
    )
    reviewer = None
    if args.review_dashboard:
        import importlib.util

        from backintel.models import build_dashboard_reviewer
        from backintel.presentation.review import DEFAULT_REVIEWER

        if not model_id.startswith(("chatgpt-plan/", "openai/")):
            raise ValueError(
                "Design review requires the OpenAI/ChatGPT writer and native Anthropic reviewer."
            )
        if any(
            importlib.util.find_spec(name) is None
            for name in ("playwright", "streamlit", "langchain_anthropic")
        ):
            raise ValueError("Install extras first: uv sync --extra dashboard --extra dashboard-review")
        reviewer = build_dashboard_reviewer(DEFAULT_REVIEWER)
    store = open_store(args.store, settings)
    try:
        record = asyncio.run(
            run_analysis(
                brief,
                model=model,
                model_id=model_id,
                store=store,
                output=Path(args.output),
                profile=args.profile,
                budget=budget,
                max_model_calls=args.max_model_calls,
                max_tool_calls=args.max_tool_calls,
                timeout_s=args.timeout,
                dashboard_reviewer=reviewer,
                dashboard_reviewer_id=DEFAULT_REVIEWER if reviewer else None,
            )
        )
    finally:
        store.close()
    print(json.dumps({k: v for k, v in record.items() if k != "messages"}, indent=2))
    if record["status"] == "failed" or (
        args.review_dashboard and not record.get("dashboard_review", {}).get("ready")
    ):
        raise SystemExit(1)


def cmd_dashboard(args, settings):
    import importlib.util
    import os
    import subprocess
    from pathlib import Path

    from backintel.artifacts import MAX_SPEC_BYTES
    from backintel.presentation import dashboard

    if args.action == "review":
        from backintel.models import build_dashboard_reviewer, build_model
        from backintel.presentation.review import review_dashboard

        if not args.reviewer_model.startswith("anthropic/"):
            raise ValueError("The design reviewer uses the native Anthropic account, independently of Sol.")
        writer_id = args.writer_model or settings.analysis_model
        if not writer_id.startswith(("chatgpt-plan/", "openai/")):
            raise ValueError(
                "Use the existing OpenAI/ChatGPT writer; the reviewer must be a different family."
            )
        reviewer = build_dashboard_reviewer(args.reviewer_model)
        writer = build_model(writer_id, reasoning_effort="medium", max_retries=0, timeout_s=120)
        result = review_dashboard(
            Path(args.directory),
            Path(args.output),
            brief=Path(args.brief).read_text(),
            reviewer=reviewer,
            reviser=writer,
            reviewer_id=args.reviewer_model,
            reviser_id=writer_id,
            max_revisions=args.max_revisions,
        )
        print(json.dumps(result, indent=2))
        if not result["ready"]:
            raise SystemExit(1)
        return
    if args.action == "generate":
        source = Path(args.report)
        if source.stat().st_size > MAX_SPEC_BYTES:
            raise ValueError("Report exceeds the specification size limit.")
        presentation = None
        if args.presentation:
            plan_path = Path(args.presentation)
            if plan_path.stat().st_size > MAX_SPEC_BYTES:
                raise ValueError("Presentation exceeds the specification size limit.")
            presentation = json.loads(plan_path.read_text())
        result = dashboard.generate_dashboard(
            json.loads(source.read_text()), Path(args.output), presentation=presentation
        )
        print(f"Dashboard ready: {result['path']}")
        return
    if importlib.util.find_spec("streamlit") is None or importlib.util.find_spec("plotly") is None:
        raise ValueError("Install the presentation packages with: uv sync --frozen --extra dashboard")
    data = Path(args.directory).resolve() / "dashboard.json"
    if not data.is_file() or data.stat().st_size > MAX_SPEC_BYTES:
        raise ValueError("Select a generated dashboard directory containing dashboard.json.")
    # Always execute our installed entry point, never a Python file supplied by a report.
    command = dashboard.streamlit_command(args.port)
    try:
        code = subprocess.call(command, env={**os.environ, "BACKINTEL_DASHBOARD_DATA": str(data)})
    except KeyboardInterrupt:
        code = 130
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="backintel", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    data = sub.add_parser("data", help="download datasets and build canonical tables and stores")
    data.add_argument("action", choices=("download", "build"))
    data.add_argument("dataset", choices=("online_retail_ii", "olist", "all"))
    data.add_argument("--force", action="store_true")
    data.set_defaults(func=cmd_data)

    stores = sub.add_parser("stores", help="build/start/stop the local native store services")
    stores.add_argument("action", choices=("build", "up", "stop"))
    stores.add_argument("kind", choices=("clickhouse", "ferretdb", "lake-iceberg"))
    stores.add_argument("--dataset", default="all", choices=("olist", "online_retail_ii", "all"))
    stores.add_argument("--force", action="store_true")
    stores.set_defaults(func=cmd_stores)

    split = sub.add_parser("split", help="load dataset splits into separate stores for the cross-store level")
    split.add_argument("action", choices=("build",))
    split.add_argument("split", nargs="?", default="all")
    split.add_argument("--force", action="store_true")
    split.set_defaults(func=cmd_split, store_for=None)

    tpch = sub.add_parser("tpch", help="generate TPC-H Parquet data for the scale level")
    tpch.add_argument("action", choices=("generate",))
    tpch.add_argument("--sf", type=float, default=1.0)
    tpch.set_defaults(func=cmd_tpch)

    replay = sub.add_parser("replay", help="build the monthly as-of snapshot stores for the ambient level")
    replay.add_argument("action", choices=("build",))
    replay.add_argument("--force", action="store_true")
    replay.set_defaults(func=cmd_replay)

    oracle = sub.add_parser("oracle", help="compute reference answers into benchmarks/answers")
    oracle.add_argument("action", choices=("build",))
    oracle.add_argument("dataset", choices=(*DATASETS, "all"))
    oracle.set_defaults(func=cmd_oracle)

    ask = sub.add_parser("ask", help="ask the analyst one question against a store")
    ask.add_argument("--store", required=True, help="e.g. sqlite:olist")
    ask.add_argument("--model", default=None)
    ask.add_argument("question")
    ask.set_defaults(func=cmd_ask)

    bench = sub.add_parser("bench", help="sync LangSmith datasets, run experiments, build the scorecard")
    bench.add_argument("action", choices=("sync", "run", "scorecard", "rescore"))
    bench.add_argument("--dataset", choices=DATASETS, default="online_retail_ii")
    bench.add_argument("--store", default=None, help="store id; default sqlite:<dataset>")
    bench.add_argument("--model", default=None)
    bench.add_argument("--levels", default=None, help="comma-separated, e.g. 1,2,3")
    bench.add_argument("--ids", default=None, help="comma-separated scenario ids")
    bench.add_argument("--limit", type=int, default=None)
    bench.add_argument("--concurrency", type=int, default=2)
    bench.add_argument("--no-judge", action="store_true")
    bench.add_argument("--no-langsmith", action="store_true", help="local run only; no experiment upload")
    bench.add_argument("--experiments", nargs="*", help="scorecard/rescore: experiment names")
    bench.set_defaults(func=cmd_bench)

    chatgpt = sub.add_parser(
        "chatgpt", help="sign in with ChatGPT to bill model calls to the operator's plan"
    )
    chatgpt.add_argument("action", choices=("login", "status", "models", "logout"))
    chatgpt.add_argument(
        "--no-browser", action="store_true", help="print the link instead of opening a browser"
    )
    chatgpt.set_defaults(func=cmd_chatgpt)

    sandbox = sub.add_parser("sandbox", help="check the Python sandbox backend")
    sandbox.add_argument("action", choices=("check",))
    sandbox.set_defaults(func=cmd_sandbox)

    analyze = sub.add_parser("analyze", help="run the opt-in SmolVM analysis/report specialist")
    analyze.add_argument("--brief", required=True, help="business brief JSON; see docs/specialist-default.md")
    analyze.add_argument("--store", required=True)
    analyze.add_argument(
        "--model", help="override BACKINTEL_ANALYSIS_MODEL (default: chatgpt-plan/gpt-6.1-sol)"
    )
    analyze.add_argument(
        "--reasoning", choices=("none", "minimal", "low", "medium", "high", "xhigh"), default="medium"
    )
    analyze.add_argument(
        "--responses-api", action="store_true", help="use the model's supported Responses path"
    )
    analyze.add_argument("--output", required=True, help="new directory for run record and artifact bundle")
    analyze.add_argument("--profile", choices=("analysis", "large"), default="analysis")
    analyze.add_argument("--timeout", type=int, default=900)
    analyze.add_argument("--max-model-calls", type=int, default=24)
    analyze.add_argument("--max-tool-calls", type=int, default=50)
    analyze.add_argument(
        "--review-dashboard",
        action="store_true",
        help="automatically inspect and revise the generated dashboard (native Anthropic reviewer)",
    )
    analyze.add_argument(
        "--max-cost-usd", type=float, help="approved API admission budget; required for OpenRouter"
    )
    analyze.add_argument(
        "--reservation-usd",
        type=float,
        help="OpenRouter per-call reservation; use provider key limits for a hard spend cap",
    )
    analyze.set_defaults(func=cmd_analyze)

    dashboard = sub.add_parser("dashboard", help="generate or locally serve a Streamlit analysis")
    actions = dashboard.add_subparsers(dest="action", required=True)
    generate = actions.add_parser(
        "generate", help="turn a retained report into a dashboard without inference"
    )
    generate.add_argument("--report", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("--presentation", help="optional validated DesignPlan JSON for the retained charts")
    serve = actions.add_parser("serve", help="serve a generated dashboard on loopback")
    serve.add_argument("directory")
    serve.add_argument("--port", type=int, default=8504)
    from backintel.presentation.review import DEFAULT_REVIEWER

    review = actions.add_parser("review", help="inspect rendered pages and revise their design at most twice")
    review.add_argument("directory")
    review.add_argument(
        "--brief", required=True, help="text or JSON file describing the reader's business question"
    )
    review.add_argument(
        "--output", required=True, help="new directory for candidates, screenshots and review"
    )
    review.add_argument("--max-revisions", type=int, choices=(0, 1, 2), default=2)
    review.add_argument("--reviewer-model", default=DEFAULT_REVIEWER)
    review.add_argument("--writer-model", help="defaults to the configured analysis specialist")
    dashboard.set_defaults(func=cmd_dashboard)

    from backintel.bench.commands import add_commands

    add_commands(sub)

    args = parser.parse_args(argv)
    settings = Settings.from_env()
    if args.command == "bench" and args.action == "run" and not args.store:
        args.store = f"sqlite:{args.dataset}"
    args.func(args, settings)


if __name__ == "__main__":
    main()
