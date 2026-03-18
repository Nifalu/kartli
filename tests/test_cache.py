import tempfile
from pathlib import Path

from kartli.cache import DiskCache, NoCache, TileCache


def test_tile_key():
    assert TileCache.tile_key("osm", 15, 100, 200) == "osm/15/100/200"


def test_no_cache():
    c = NoCache()
    c.put("key", b"data")
    assert c.get("key") is None


def test_disk_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = DiskCache(base_dir=Path(tmpdir))
        assert c.get("test/1/2/3") is None
        c.put("test/1/2/3", b"hello")
        assert c.get("test/1/2/3") == b"hello"
