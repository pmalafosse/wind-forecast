"""Test logging configuration."""

import logging
from pathlib import Path

import pytest

from windforecast.logging import configure_logging


def test_configure_logging_verbose(caplog):
    """Test that verbose mode sets DEBUG level."""
    configure_logging(verbose=True)
    logger = logging.getLogger("windforecast")
    assert logger.getEffectiveLevel() == logging.DEBUG


def test_configure_logging_normal(caplog):
    """Test that normal mode sets INFO level."""
    configure_logging(verbose=False)
    logger = logging.getLogger("windforecast")
    assert logger.getEffectiveLevel() == logging.INFO


def test_configure_logging_with_file(tmp_path):
    """Test that log file is created and written to."""
    log_file = tmp_path / "test.log"
    configure_logging(log_file=log_file)
    logger = logging.getLogger("windforecast")

    test_message = "Test log message"
    logger.info(test_message)

    assert log_file.exists()
    content = log_file.read_text()
    assert test_message in content
