"""Deterministic evidence storage in Git, with a verified disposable local cache."""
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(root):
    source = Path(root) / 'data/performance_evidence'
    manifest = json.loads((source / 'manifest.json').read_text())
    storage = manifest.get('storage')
    if storage:
        if storage.get('format') != 'tar+gzip' or storage.get('file') != 'snapshot.tar.gz':
            raise ValueError('Unsupported performance evidence storage')
        if digest(source / storage['file']) != storage['sha256']:
            raise ValueError('Evidence bundle hash mismatch; restore it or use --full-refresh')
    return manifest


def pack_evidence(source):
    """Pack verified files with stable member order, metadata and gzip timestamp."""
    source = Path(source)
    manifest = json.loads((source / 'manifest.json').read_text())
    inventory = manifest['evidenceHashes']
    if not inventory:
        raise ValueError('Cannot pack empty performance evidence')
    with tempfile.TemporaryDirectory(prefix='.pack-', dir=source) as temporary:
        archive = Path(temporary) / 'snapshot.tar.gz'
        with archive.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.USTAR_FORMAT) as tar:
                for name, expected in sorted(inventory.items()):
                    parts = PurePosixPath(name).parts
                    if len(parts) != 2 or parts[0] not in {'games', 'histories'} or not parts[1].endswith('.json'):
                        raise ValueError('Invalid evidence member path')
                    content = (source / name).read_bytes()
                    if hashlib.sha256(content).hexdigest() != expected:
                        raise ValueError(f'Cannot pack changed evidence: {name}')
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(content))
        manifest['storage'] = dict(format='tar+gzip', file='snapshot.tar.gz', sha256=digest(archive))
        staged_manifest = Path(temporary) / 'manifest.json'
        staged_manifest.write_text(json.dumps(manifest, indent=2) + '\n')
        archive.replace(source / 'snapshot.tar.gz')
        staged_manifest.replace(source / 'manifest.json')
    # Only validated source files are removed, after their packed replacement exists.
    for folder in ('games', 'histories'):
        if (source / folder).exists():
            shutil.rmtree(source / folder)
    return manifest


def evidence_source(root):
    """Materialize a hash-checked bundle outside versioned data directories."""
    root = Path(root)
    source = root / 'data/performance_evidence'
    manifest = verify_bundle(root)
    if not manifest.get('storage'):
        # Fixture and import staging support; published source uses the bundle.
        return source
    cache = root / '.cache/performance/evidence' / manifest['storage']['sha256']
    inventory = manifest['evidenceHashes']
    valid = cache.is_dir() and all((cache / name).is_file() and digest(cache / name) == expected
                                   for name, expected in inventory.items())
    if not valid:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.unpack-', dir=cache.parent) as temporary:
            target = Path(temporary) / 'evidence'
            target.mkdir()
            seen = set()
            with tarfile.open(source / 'snapshot.tar.gz', mode='r:gz') as tar:
                for member in tar:
                    parts = PurePosixPath(member.name).parts
                    if (member.name not in inventory or member.name in seen or not member.isfile()
                            or len(parts) != 2 or parts[0] not in {'games', 'histories'}
                            or not parts[1].endswith('.json') or member.size > 4_000_000):
                        raise ValueError('Invalid evidence bundle member')
                    content = tar.extractfile(member).read()
                    if hashlib.sha256(content).hexdigest() != inventory[member.name]:
                        raise ValueError(f'Evidence member hash mismatch: {member.name}')
                    destination = target / member.name
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(content)
                    seen.add(member.name)
            if seen != set(inventory):
                raise ValueError('Evidence bundle inventory is incomplete')
            if cache.exists():
                shutil.rmtree(cache)
            target.rename(cache)
    # Input bindings can change while the packed game bytes remain identical.
    shutil.copyfile(source / 'manifest.json', cache / 'manifest.json')
    return cache
