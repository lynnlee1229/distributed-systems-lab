#!/usr/bin/env python3
"""Download a pinned upstream archive, verify known release-asset SHA-256."""
import hashlib,platform,subprocess,tarfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='3.6.6'
HASHES={
'darwin-arm64':'8e554646efaaab2043e37ee7970058b458511b49606c89ea2764f3550aa34934',
'darwin-amd64':'b542f56ba15096151bb2bef402299ec3fcdd6fad971f56c1562b6a75434c7dea',
'linux-amd64':'887afaa4a99f22d802ccdfbe65730a5e79aa5c9ce2c8799c67e9d804c50ecedb',
'linux-arm64':'8a15f5427c111ff4692753682374970fb68878401d946c2c28bdad6857db652f'}
def main():
    target=platform.system().lower()+'-'+{'aarch64':'arm64','arm64':'arm64','x86_64':'amd64'}.get(platform.machine(),platform.machine())
    if target not in HASHES: raise SystemExit('Supported: Linux/macOS, amd64/arm64')
    folder=ROOT/'build/runtime';folder.mkdir(parents=True,exist_ok=True)
    ext='zip' if target.startswith('darwin') else 'tar.gz'
    archive=ROOT/'build'/f'etcd-v{VERSION}-{target}.{ext}'
    if not archive.exists():
        urllib.request.urlretrieve(f'https://storage.googleapis.com/etcd/v{VERSION}/{archive.name}',archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==HASHES[target], 'archive checksum mismatch'
    prefix=f'etcd-v{VERSION}-{target}/'
    # Extract only the three named executables, never arbitrary archive paths.
    for name in ('etcd','etcdctl','etcdutl'):
        if ext=='zip':
            with zipfile.ZipFile(archive) as z: raw=z.read(prefix+name)
        else:
            with tarfile.open(archive) as t: raw=t.extractfile(prefix+name).read()
        out=folder/name;out.write_bytes(raw);out.chmod(0o755)
    subprocess.run([str(folder/'etcd'),'--version'],check=True)
    print('Verified upstream archive SHA-256:',HASHES[target])
if __name__=='__main__':main()
