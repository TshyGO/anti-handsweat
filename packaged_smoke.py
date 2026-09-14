"""Bounded self-test of the actual executable; no real photos or network access."""
import json
from pathlib import Path
import traceback


def run(report: Path, app_class, resource_root: Path) -> int:
    result = {'status': 'FAILED', 'checks': [], 'real_raw_decoded': False}
    root = None
    try:
        import sys
        import platform
        import tkinter as tk
        import numpy as np
        import tifffile
        import rawpy
        from pipeline import environment, rgb_to_y, mean_abs_diff, save_analysis, save_preview
        result['environment'] = environment()
        result['machine'] = platform.machine()
        result['frozen'] = bool(getattr(sys, 'frozen', False))
        rawpy.Params(demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                     gamma=(1, 1), output_bps=16, no_auto_bright=True,
                     adjust_maximum_thr=0.0, bright=1.0, no_auto_scale=False,
                     use_camera_wb=False, use_auto_wb=False, user_wb=[1, 1, 1, 1],
                     output_color=rawpy.ColorSpace.sRGB, user_flip=0,
                     highlight_mode=rawpy.HighlightMode.Clip,
                     fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                     noise_thr=None, median_filter_passes=0)
        result['checks'].append('rawpy_libraw_import_and_params')
        help_file = resource_root / 'PACKAGED_README.html'
        if 'Y_linear32.tif' not in help_file.read_text(encoding='utf-8'):
            raise RuntimeError('Bundled help missing or invalid')
        result['checks'].append('bundled_help')
        report.parent.mkdir(parents=True, exist_ok=True)
        y = rgb_to_y(np.full((10, 10, 3), 65535, dtype=np.uint16))
        np.testing.assert_allclose(y, 1, atol=1e-7)
        clean = np.full((10, 10), 0.25, dtype=np.float32)
        changed = clean.copy()
        changed[:5, :5] += 0.125
        diff, value = mean_abs_diff(clean, changed)
        if value != 0.03125:
            raise RuntimeError(f'Unexpected synthetic metric: {value}')
        save_analysis(diff, report.parent/'smoke.tif', {'synthetic': True})
        np.testing.assert_array_equal(tifffile.imread(report.parent/'smoke.tif'), diff)
        save_preview(diff, report.parent/'smoke.png')
        result['checks'].append('synthetic_tiff_and_preview_roundtrip')
        root = tk.Tk()
        root.withdraw()
        app = app_class(root)
        root.update_idletasks()
        app.busy(True)
        if not app.is_busy or any(str(b['state']) != 'disabled' for b in app.buttons):
            raise RuntimeError('GUI busy state failed')
        app.busy(False)
        if app.is_busy or any(str(b['state']) != 'normal' for b in app.buttons):
            raise RuntimeError('GUI ready state failed')
        if result['frozen'] and Path(app.out.get()) != Path.home()/'CoatingImaging'/'output':
            raise RuntimeError('Bundled output directory must be outside application')
        result['checks'].append('gui_creation_and_busy_state')
        result['status'] = 'PASS'
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        if root is not None:
            root.destroy()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if result['status'] == 'PASS' else 1
