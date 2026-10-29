from app.ui.components import status_counts, toggle_selection


def test_toggle_selection_preserves_order_and_toggles_values() -> None:
    assert toggle_selection(["a", "b"], "a") == ["b"]
    assert toggle_selection(["b"], "a") == ["b", "a"]


def test_status_counts_only_counts_known_document_states() -> None:
    documents = [{"status": "indexed"}, {"status": "failed"}, {"status": "unknown"}]
    assert status_counts(documents) == {"uploaded": 0, "processing": 0, "indexed": 1, "failed": 1}
