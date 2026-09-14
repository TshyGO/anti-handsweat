"""Extract and smoke-test the shipped archive, not the source interpreter."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    archive = Path(sys.argv[1]).resolve()
    expected_arch = sys.argv[2]
    with tempfile.TemporaryDirectory(prefix='coating package 中文 ') as tmp:
        work = Path(tmp)
        extracted = work/'extracted'
        shutil.unpack_archive(archive, extracted)
        required = ['开始使用.html', 'imagej/01_difference_fixed_roi.ijm',
                    'imagej/02_check_known_numbers.ijm', 'demo/expected_values.json',
                    'docs/方法与输出说明.md']
        for name in required:
            if not (extracted/name).is_file():
                raise RuntimeError(f'Archive missing {name}')
        if sys.platform == 'darwin':
            executable = extracted/'CoatingImaging.app/Contents/MacOS/CoatingImaging'
        else:
            executable = extracted/'CoatingImaging/CoatingImaging.exe'
        report = work/'self-test'/'result.json'
        env = {k: v for k, v in os.environ.items()
               if k not in ('PYTHONPATH', 'PYTHONHOME', 'TCL_LIBRARY', 'TK_LIBRARY')}
        # Unrelated cwd + Unicode/space paths expose accidental source dependencies.
        completed = subprocess.run([str(executable), '--self-test', str(report)],
                                   cwd=work, env=env, timeout=60)
        if not report.is_file():
            raise RuntimeError(f'Packaged app did not write a report; exit={completed.returncode}')
        evidence = Path(__file__).resolve().parents[1]/'build'/'package-smoke.json'
        evidence.parent.mkdir(exist_ok=True)
        shutil.copy2(report, evidence)
        result = json.loads(report.read_text(encoding='utf-8'))
        print(json.dumps(result, ensure_ascii=True, indent=2))
        if completed.returncode != 0 or result['status'] != 'PASS' or not result['frozen']:
            raise RuntimeError('Packaged executable self-test failed')
        if result['machine'].lower() != expected_arch.lower():
            raise RuntimeError('Packaged architecture does not match artifact label')
        expected_checks = {'rawpy_libraw_import_and_params', 'bundled_help',
                           'synthetic_tiff_and_preview_roundtrip', 'gui_creation_and_busy_state'}
        if set(result['checks']) != expected_checks:
            raise RuntimeError('Incomplete packaged application checks')


if __name__ == '__main__':
    main()
