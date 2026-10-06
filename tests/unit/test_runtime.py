from private_assistent.runtime import run_once


def test_run_once_returns_message():
    reply = run_once("hello")
    assert "hello" in reply
    assert "model=" in reply
