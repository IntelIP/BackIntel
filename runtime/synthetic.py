"""Reproducible, explicitly synthetic histories for the two configured domains."""
from runtime.simulation import load_scenario


def history(name: str, count=24) -> tuple[dict, list[dict], list[dict]]:
    task = load_scenario(name)["task"]
    rows, outcomes = [], []
    support = name == "support"
    for i in range(count):
        at = i * 3
        structured = (i * 7 % 11) / 10
        semantic = (i * 5 % 7) / 6
        entity = ("Accounts" if i % 2 == 0 else "Access") if support else ("Pump-A" if i % 2 == 0 else "Pump-B")
        values = {"id": f"{name}-{i:03}", "entity": entity, "event_at": at, "available_at": at,
                  "revision": 1, "content": ("Login failed" if semantic >= .5 else "Service working") if support else str(semantic * 10)}
        row = {task["fields"][k]: v for k, v in values.items()}
        row[task["measures"][0]["field"]] = structured * (100 if support else 80) + (0 if support else 20)
        rows.append(row)
        outcomes.append({"source_id": values["id"], "entity": entity, "event_at": at,
                         "available_at": at + task["target"]["horizon"], "revision": 1,
                         "value": int(structured + semantic >= 1) if support else round(2 * structured + 3 * semantic, 6)})
    return task, rows, outcomes
