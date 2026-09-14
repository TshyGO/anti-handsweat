"""Assemble an existing PyInstaller build; preserve macOS app symlinks."""
from pathlib import Path
import shutil
import sys


def main():
    artifact = sys.argv[1]
    root = Path(__file__).resolve().parents[1]
    package = root/'package'
    package.mkdir(exist_ok=False)
    for directory in ('imagej', 'demo'):
        shutil.copytree(root/directory, package/directory)
    docs = package/'docs'
    docs.mkdir()
    for name in ('README.md', 'CHANGELOG.md', 'VALIDATION.md', 'requirements.txt',
                 '方法与输出说明.md'):
        shutil.copy2(root/name, docs/name)
    shutil.copy2(root/'PACKAGED_README.html', package/'开始使用.html')
    if sys.platform == 'darwin':
        source = root/'dist'/'CoatingImaging.app'
        if not (source/'Contents'/'MacOS'/'CoatingImaging').is_file():
            raise RuntimeError('macOS .app executable is missing')
        shutil.copytree(source, package/source.name, symlinks=True)
        fmt = 'gztar'
    elif sys.platform == 'win32':
        source = root/'dist'/'CoatingImaging'
        if not (source/'CoatingImaging.exe').is_file():
            raise RuntimeError('Windows executable is missing')
        shutil.copytree(source, package/source.name)
        fmt = 'zip'
    else:
        raise RuntimeError('Only macOS and Windows packages are supported')
    print(shutil.make_archive(str(root/artifact), fmt, root_dir=package))


if __name__ == '__main__':
    main()
