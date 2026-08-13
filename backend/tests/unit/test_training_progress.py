from io import StringIO

from training.progress import TerminalProgress


def test_terminal_progress_reports_completion_and_eta_when_total_is_known():
    stream = StringIO()

    progress = TerminalProgress("tfidf evaluation", total=4, stream=stream)
    progress.update(4)

    output = stream.getvalue()
    assert "tfidf evaluation" in output
    assert "4/4" in output
    assert "100.0%" in output
    assert "ETA" in output


def test_terminal_progress_clears_a_previous_longer_line_before_redraw():
    stream = StringIO()
    progress = TerminalProgress("tfidf training", total=2, stream=stream)

    progress.update(1, "reduce embeddings")
    progress.update(2, "verify artifact")

    output = stream.getvalue()
    assert output
    assert output.count("\x1b[2K") == 2
