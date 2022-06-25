import pytest
from vcr import VCR
from vcr.persisters.filesystem import FilesystemPersister as VCRFilesystemPersister

from . import VCR_DIR


@pytest.fixture(scope="session")
def vcr():
    vcr = VCR(decode_compressed_response=False)

    class Persister:
        @classmethod
        def _add_prefix(cls, cassette_path):
            if isinstance(cassette_path, str):
                if not cassette_path.startswith(VCR_DIR.as_posix()):
                    cassette_path = VCR_DIR / cassette_path

            return cassette_path

        @classmethod
        def load_cassette(cls, cassette_path, serializer):
            return VCRFilesystemPersister.load_cassette(
                cassette_path=cls._add_prefix(cassette_path), serializer=serializer
            )

        @classmethod
        def save_cassette(cls, cassette_path, cassette_dict, serializer):
            return VCRFilesystemPersister.save_cassette(
                cassette_path=cls._add_prefix(cassette_path),
                cassette_dict=cassette_dict,
                serializer=serializer,
            )

    vcr.register_persister(Persister)
    return vcr
