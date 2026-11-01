"""Packed evidence stays reproducible and rebuilds offline without a warm cache."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

from mega.inputs.evidence_bundle import evidence_source, pack_evidence
from mega.stats.performance import build_performance
import test_performance


class EvidenceBundleTests(unittest.TestCase):
    def test_deterministic_bundle_and_cold_cache_preserve_calculations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'first'
            root.mkdir()
            source = test_performance.PerformanceTests().fixture(root)
            original = build_performance(root)['outputHashes']
            expected = {name: (source / name).read_bytes()
                        for name in json.loads((source / 'manifest.json').read_text())['evidenceHashes']}
            second = Path(temporary) / 'second'
            shutil.copytree(root, second)
            pack_evidence(source)
            pack_evidence(second / 'data/performance_evidence')
            self.assertEqual((source / 'snapshot.tar.gz').read_bytes(),
                             (second / 'data/performance_evidence/snapshot.tar.gz').read_bytes())
            self.assertEqual({p.name for p in source.iterdir()}, {'manifest.json', 'snapshot.tar.gz'})
            shutil.rmtree(root / '.cache')
            self.assertEqual(build_performance(root)['outputHashes'], original)
            expanded = evidence_source(root)
            self.assertIn('.cache', expanded.parts)
            self.assertEqual(expected, {name: (expanded / name).read_bytes() for name in expected})
            (expanded / 'games/1.json').write_text('corrupt local cache')
            self.assertEqual((evidence_source(root) / 'games/1.json').read_bytes(), expected['games/1.json'])

    def test_damaged_bundle_fails_instead_of_using_warm_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = test_performance.PerformanceTests().fixture(root)
            pack_evidence(source)
            evidence_source(root)
            with (source / 'snapshot.tar.gz').open('ab') as stream:
                stream.write(b'changed')
            with self.assertRaisesRegex(ValueError, 'bundle hash mismatch'):
                build_performance(root)

    def test_missing_members_and_unsafe_paths_are_rejected(self):
        for name in ('games/1.json', '../outside.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = test_performance.PerformanceTests().fixture(root)
                manifest = json.loads((source / 'manifest.json').read_text())
                content = (source / 'games/1.json').read_bytes()
                archive = source / 'snapshot.tar.gz'
                with tarfile.open(archive, mode='w:gz') as tar:
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    tar.addfile(info, io.BytesIO(content))
                manifest['storage'] = dict(format='tar+gzip', file=archive.name,
                                          sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
                (source / 'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    evidence_source(root)
                self.assertFalse((root / '.cache/performance/outside.json').exists())


if __name__ == '__main__':
    unittest.main()
