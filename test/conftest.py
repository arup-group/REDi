# conftest.py

# Fixture files
pytest_plugins = [
    "test.fixtures.assets",
]


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """





def pytest_unconfigure(config):
    """
    called before test process is exited.
    """
