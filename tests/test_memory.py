import pytest

from bob.index import Index
from bob.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


def add_sample(store):
    store.add("pitfall", "Build with -j6", "Full parallel build saturates RAM, use -j6.",
              body="make -j6 from fg_slam/build", paths=["fg_slam/CMakeLists.txt"], tags=["build"])
    store.add("recipe", "Add a lidar factor", "Edit lidar_factor.hpp then register it in the graph.",
              paths=["fg_slam/include/lidar_factor.hpp"], tags=["lidar", "factor"])


def test_memory_is_stored_outside_the_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    Store(project).add("map", "Layout", "Folders.")
    assert list(project.iterdir()) == []


def test_add_then_get_round_trips(store):
    entry = store.add("command", "Run tests", "ctest from build dir.", body="ctest -j6")
    assert store.get(entry.id) == entry


def test_ids_stay_unique_for_same_title(store):
    first = store.add("map", "Layout", "Folders.")
    second = store.add("map", "Layout", "Folders again.")
    assert first.id != second.id


def test_add_rejects_oversized_summary(store):
    with pytest.raises(ValueError, match="summary"):
        store.add("map", "Layout", "x" * 200)


def test_get_rejects_path_traversal(store):
    assert store.get("../../etc/passwd") is None


def test_search_finds_by_text(store):
    add_sample(store)
    results = Index(store).search("parallel build RAM")
    assert [e.title for e in results] == ["Build with -j6"]


def test_search_boosts_entries_listing_the_touched_file(store):
    add_sample(store)
    results = Index(store).search("", paths=["fg_slam/include/lidar_factor.hpp"])
    assert [e.title for e in results] == ["Add a lidar factor"]


def test_search_survives_punctuation_in_query(store):
    add_sample(store)
    assert Index(store).search('lidar" OR (factor*') != []


def test_index_sees_entries_added_after_first_search(store):
    index = Index(store)
    assert index.search("lidar") == []
    add_sample(store)
    assert index.search("lidar") != []


def test_feedback_promotes_then_retires(store):
    entry = store.add("recipe", "Do thing", "Steps.")
    store.record_feedback(entry.id, useful=True)
    assert store.record_feedback(entry.id, useful=True).status == "trusted"
    for _ in range(4):
        retired = store.record_feedback(entry.id, useful=False)
    assert retired.status == "retired"
    assert Index(store).search("Do thing") == []


def test_update_replaces_only_given_fields(store):
    entry = store.add("command", "Run eval", "Old summary.", body="old body", tags=["eval"])
    updated = store.update(entry.id, summary="New summary.")
    assert (updated.summary, updated.body, updated.tags) == ("New summary.", "old body", ["eval"])
    assert store.get(entry.id).summary == "New summary."


def test_update_revives_a_retired_entry(store):
    entry = store.add("recipe", "Do thing", "Steps.")
    for _ in range(2):
        store.record_feedback(entry.id, useful=False)
    assert store.get(entry.id).status == "retired"
    revived = store.update(entry.id, body="Fixed steps.")
    assert (revived.status, revived.wrong) == ("candidate", 0)


def test_update_rejects_oversized_summary_and_keeps_entry(store):
    entry = store.add("map", "Layout", "Folders.")
    with pytest.raises(ValueError, match="summary"):
        store.update(entry.id, summary="x" * 200)
    assert store.get(entry.id).summary == "Folders."


def test_remove_hides_entry_but_keeps_a_copy(store):
    entry = store.add("pitfall", "Old advice", "Outdated.")
    store.remove(entry.id)
    assert store.get(entry.id) is None
    assert Index(store).search("Old advice") == []
    assert (store.removed_dir / f"{entry.id}.md").exists()


def test_update_and_remove_unknown_id_raise(store):
    with pytest.raises(KeyError):
        store.update("nope", summary="x")
    with pytest.raises(KeyError):
        store.remove("nope")
