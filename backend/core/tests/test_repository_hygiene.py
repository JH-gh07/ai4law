from scripts.check_repository_hygiene import active_path_violations


def test_migration_ledger_may_record_legacy_paths_as_evidence() -> None:
    assert active_path_violations(["config/local_new_parity_manifest.json"]) == []
