import tempfile
from pathlib import Path

from kartli.cache import DiskCache, NoCache, TileCache


def test_tile_key():
    assert TileCache.tile_key("osm", 15, 100, 200) == "osm/15/100/200"


def test_tile_key_different_prefixes():
    k1 = TileCache.tile_key("osm", 15, 100, 200)
    k2 = TileCache.tile_key("swisstopo", 15, 100, 200)
    assert k1 != k2


def test_no_cache_always_misses():
    c = NoCache()
    c.put("key", b"data")
    assert c.get("key") is None


def test_disk_cache_miss():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = DiskCache(base_dir=Path(tmpdir))
        assert c.get("nonexistent/1/2/3") is None


def test_disk_cache_put_and_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = DiskCache(base_dir=Path(tmpdir))
        c.put("test/1/2/3", b"hello")
        assert c.get("test/1/2/3") == b"hello"


def test_disk_cache_overwrites():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = DiskCache(base_dir=Path(tmpdir))
        c.put("test/key", b"first")
        c.put("test/key", b"second")
        assert c.get("test/key") == b"second"


def test_disk_cache_creates_subdirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = DiskCache(base_dir=Path(tmpdir))
        c.put("deep/nested/path/tile", b"data")
        assert c.get("deep/nested/path/tile") == b"data"


def test_disk_cache_binary_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = DiskCache(base_dir=Path(tmpdir))
        data = bytes(range(256))
        c.put("binary/tile", data)
        assert c.get("binary/tile") == data
