from private_assistent.context import ContextConfig, ContextManager, SQLiteContextStore


def test_context_manager_persists_and_builds_recent_window(tmp_path):
    store = SQLiteContextStore(tmp_path / "context.db")
    manager = ContextManager(store, config=ContextConfig(max_messages=3, max_chars=1000))

    manager.append_user_message("s1", "first")
    manager.append_assistant_message("s1", "second")
    manager.append_user_message("s1", "third")
    manager.append_assistant_message("s1", "fourth")

    built = manager.build_context("s1")

    assert built.total_messages == 4
    assert built.included_messages == 3
    assert built.truncated is True
    assert [item["content"] for item in built.messages] == ["second", "third", "fourth"]


def test_context_store_lists_and_clears_sessions(tmp_path):
    store = SQLiteContextStore(tmp_path / "context.db")
    manager = ContextManager(store)

    manager.append_user_message("s1", "hello context")
    sessions = manager.list_sessions()

    assert sessions[0].id == "s1"
    assert sessions[0].message_count == 1

    manager.clear_session("s1")

    assert manager.list_messages("s1") == []
