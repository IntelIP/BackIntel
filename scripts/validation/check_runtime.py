"""Run offline runtime contracts only against an explicitly isolated test database."""
import os
import unittest

from psycopg.conninfo import conninfo_to_dict

from runtime.bootstrap import initialize


def main() -> int:
    test_dsn = os.environ.get("BACKINTEL_TEST_DATABASE_URL", "")
    database = conninfo_to_dict(test_dsn).get("dbname", "")
    if not test_dsn or not (database.startswith("test_") or database.endswith("_test")):
        raise RuntimeError("Runtime checks require an explicit test-named database")
    os.environ["BACKINTEL_APP_DATABASE_URL"] = test_dsn
    initialize()
    suite = unittest.TestSuite()
    for pattern in ("test_costs.py", "test_replay_ledger.py", "test_jev.py"):
        suite.addTests(unittest.defaultTestLoader.discover("tests", pattern=pattern))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
