import pytest

from helpers import write_photos


@pytest.fixture(scope="session")
def samples_dir(tmp_path_factory):
    """A folder of fake template photos, built once for the whole test run."""
    return write_photos(tmp_path_factory.mktemp("samples"))


@pytest.fixture(scope="session")
def writer(samples_dir):
    from penmimic import Writer
    return Writer.from_samples(samples_dir, seed=1)


