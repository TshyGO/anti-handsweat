"""Experimental coating-image pipeline. Local files only; no network operations.
Numerical output is NOT calibrated luminance, CIE L*, or contaminant mass.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import platform
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import numpy as np
import tifffile
from PIL import Image
from platform_paths import discover_exiftool

APP_VERSION = '0.1.1-mac-development'
Y_WEIGHTS = (0.2126, 0.7152, 0.0722)
CRITICAL_TAGS = ('Make', 'Model', 'LensModel', 'ISO', 'ExposureTime', 'FNumber', 'FocalLength', 'Orientation')
EXIF_TAGS = CRITICAL_TAGS + ('DateTimeOriginal', 'SubSecTimeOriginal', 'WhiteBalance', 'ExposureProgram', 'FileType', 'Compression', 'ExifToolVersion')

PROCESSING_CONFIG = {'demosaic': 'AHD', 'half_size': False, 'four_color_rgb': False,
            'use_camera_wb': False, 'use_auto_wb': False, 'no_auto_bright': True,
            'adjust_maximum_thr': 0.0, 'bright': 1.0, 'gamma': [1, 1],
            'output_bps': 16, 'output_color': 'sRGB', 'user_flip': 0,
            'highlight_mode': 'Clip', 'no_auto_scale': False,
            'black_level_policy': 'LibRaw file metadata/default correction, recorded per file',
            'saturation_policy': 'LibRaw file metadata/default white level, recorded per file'}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def config_hash(profile: dict) -> str:
    return hashlib.sha256(json.dumps(profile, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def exif_metadata(path: Path, executable: str = '') -> dict:
    """Read selected tags only. Missing metadata never becomes a guessed value."""
    exe = discover_exiftool(executable, Path(__file__).resolve().parent)
    if not exe:
        return {'status': 'unavailable', 'reason': 'ExifTool not configured', 'tags': {}}
    args = [exe, '-json', '-n', '-charset', 'filename=UTF8', *('-'+t for t in EXIF_TAGS), str(path.resolve())]
    try:
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        result = subprocess.run(args, capture_output=True, timeout=60, check=True, **options)
        data = json.loads(result.stdout.decode('utf-8'))[0]
        tags = {k: data.get(k) for k in EXIF_TAGS}
        return {'status': 'read', 'tags': tags,
                'stderr': result.stderr.decode('utf-8', errors='replace').strip()}
    except Exception as exc:
        return {'status': 'unavailable', 'reason': str(exc), 'tags': {}}

def compare_capture(reference: dict, actual: dict) -> dict:
    differences, unknown = {}, []
    for k in CRITICAL_TAGS:
        a, b = reference.get('tags', {}).get(k), actual.get('tags', {}).get(k)
        if a is None or b is None:
            unknown.append(k)
            continue
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            same = math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-10)
        else:
            same = str(a) == str(b)
        if not same:
            differences[k] = {'reference': a, 'actual': b}
    return {'differences': differences, 'missing_or_unchecked': unknown,
            'status': 'mismatch' if differences else ('incomplete' if unknown else 'matched_recorded_tags')}

def sensor_info(raw: Any) -> dict:
    pattern = raw.raw_pattern
    return {
        'visible_shape': [int(v) for v in raw.raw_image_visible.shape],
        'color_desc': raw.color_desc.decode('ascii', errors='replace'),
        'num_colors': int(raw.num_colors),
        'raw_pattern': pattern.tolist() if pattern is not None else None,
        'camera_whitebalance': [float(v) for v in raw.camera_whitebalance],
        'black_level_per_channel': [int(v) for v in raw.black_level_per_channel],
        'white_level': int(raw.white_level),
        'camera_white_level_per_channel': [int(v) for v in raw.camera_white_level_per_channel] if raw.camera_white_level_per_channel is not None else None,
    }

def environment() -> dict:
    import rawpy
    return {'app': APP_VERSION, 'python': sys.version, 'platform': platform.platform(),
            'rawpy': rawpy.__version__, 'libraw': list(rawpy.libraw_version),
            'numpy': np.__version__, 'tifffile': tifffile.__version__,
            'machine': platform.machine(), 'system': platform.system(),
            'libraw_compiled': list(getattr(rawpy, 'libraw_version_compiled', rawpy.libraw_version)),
            'rawpy_flags': dict(rawpy.flags)}

def make_profile(reference_path: Path, exiftool: str = '') -> dict:
    """Freeze this reference file's as-shot WB for all files. NOT a WB calibration."""
    import rawpy
    with rawpy.imread(str(reference_path)) as raw:
        info = sensor_info(raw)
    if info['color_desc'] != 'RGBG' or info['raw_pattern'] is None or np.shape(info['raw_pattern']) != (2, 2):
        raise ValueError('V0.1 currently accepts Bayer RGBG RAW only; this file requires a separate validated profile.')
    wb = info['camera_whitebalance'][:]
    notes = []
    if len(wb) == 4 and wb[3] == 0 and wb[1] > 0:
        wb[3] = wb[1]
        notes.append('Reference G2 multiplier was 0; explicitly copied G1 for RGBG.')
    if len(wb) != 4 or any(not math.isfinite(x) or x <= 0 for x in wb):
        raise ValueError('Reference RAW does not provide four usable WB multipliers.')
    return {
        'schema': 1, 'status': 'DEVELOPMENT_NOT_VALIDATED',
        'reference_file': str(reference_path.resolve()), 'reference_sha256': sha256(reference_path),
        'reference_exif': exif_metadata(reference_path, exiftool), 'sensor': info,
        'user_wb': wb, 'wb_origin': 'one_reference_as_shot_values_fixed_for_batch_not_calibrated',
        'notes': notes, 'environment': environment(),
        'processing': dict(PROCESSING_CONFIG),
        'analysis': {'Y_weights': list(Y_WEIGHTS), 'normalization_denominator': 65535,
            'unit': 'normalized_linear_output_code_not_physical_luminance',
            'alignment': 'not_performed', 'thresholding': 'not_performed'}
    }

def rgb_to_y(rgb: np.ndarray) -> np.ndarray:
    if rgb.dtype != np.uint16 or rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError('Expected H x W x 3 uint16 output from fixed RAW decoding.')
    y = np.zeros(rgb.shape[:2], dtype=np.float32)
    for c, weight in enumerate(Y_WEIGHTS):
        y += rgb[..., c].astype(np.float32) * np.float32(weight / 65535.0)
    if not np.isfinite(y).all():
        raise ValueError('Non-finite Y values.')
    return y

def mean_abs_diff(clean: np.ndarray, changed: np.ndarray, roi: tuple[int,int,int,int] | None = None) -> tuple[np.ndarray, float]:
    if clean.ndim != 2 or clean.shape != changed.shape:
        raise ValueError('Same-size single-channel aligned images are required.')
    if not np.isfinite(clean).all() or not np.isfinite(changed).all():
        raise ValueError('Non-finite input pixels are not allowed.')
    diff = np.abs(changed.astype(np.float32) - clean.astype(np.float32))
    if roi is None:
        region = diff
    else:
        x, y, w, h = roi
        if min(x,y) < 0 or min(w,h) <= 0 or x+w > diff.shape[1] or y+h > diff.shape[0]:
            raise ValueError('ROI is outside the image.')
        region = diff[y:y+h, x:x+w]
    return diff, float(np.mean(region, dtype=np.float64))

def save_analysis(y: np.ndarray, path: Path, description: dict) -> None:
    if y.ndim != 2 or y.dtype != np.float32 or not np.isfinite(y).all():
        raise ValueError('Analysis TIFF requires a finite 2D float32 array.')
    tifffile.imwrite(path, y, photometric='minisblack', metadata=None,
                     description=json.dumps(description, ensure_ascii=True))
    readback = tifffile.imread(path)
    if readback.dtype != np.float32 or not np.array_equal(y, readback):
        raise RuntimeError('TIFF readback validation failed.')

def save_preview(y: np.ndarray, path: Path) -> None:
    step = max(1, math.ceil(max(y.shape) / 1200))
    a = np.clip(y[::step, ::step], 0, 1)
    display = np.where(a <= 0.0031308, 12.92*a, 1.055*np.power(a, 1/2.4)-0.055)
    Image.fromarray(np.round(display * 255).astype(np.uint8)).save(path)

def process_one(source: Path, dest: Path, profile: dict, exiftool: str, save_rgb: bool = True) -> dict:
    import rawpy
    if (profile.get('schema') != 1 or profile.get('processing') != PROCESSING_CONFIG
        or profile.get('analysis', {}).get('Y_weights') != list(Y_WEIGHTS)
        or profile.get('analysis', {}).get('normalization_denominator') != 65535):
        raise ValueError('Unsupported profile.')
    current = environment()
    for key in ('rawpy', 'libraw', 'numpy', 'tifffile', 'machine', 'system'):
        if current[key] != profile['environment'].get(key):
            raise ValueError(f'{key} differs from the profile. Create a new DEVELOPMENT profile; do not mix outputs.')
    wb = profile['user_wb']
    if len(wb) != 4 or any(not math.isfinite(v) or v <= 0 for v in wb):
        raise ValueError('Invalid fixed WB coefficients.')
    exif = exif_metadata(source, exiftool)
    qc = compare_capture(profile['reference_exif'], exif)
    if qc['differences']:
        raise ValueError('Capture metadata differs from reference: ' + json.dumps(qc['differences'], ensure_ascii=False))
    with rawpy.imread(str(source)) as raw:
        info = sensor_info(raw)
        for k in ('visible_shape', 'color_desc', 'raw_pattern'):
            if info[k] != profile['sensor'][k]:
                raise ValueError('Sensor layout mismatch: '+k)
        rgb = raw.postprocess(demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
            half_size=False, four_color_rgb=False, use_camera_wb=False, use_auto_wb=False,
            user_wb=wb, output_color=rawpy.ColorSpace.sRGB, output_bps=16, user_flip=0,
            no_auto_bright=True, adjust_maximum_thr=0.0, bright=1.0,
            gamma=(1, 1), highlight_mode=rawpy.HighlightMode.Clip,
            no_auto_scale=False, fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
            noise_thr=None, median_filter_passes=0)
    source_hash = sha256(source)
    stem = re.sub(r'[^\w.-]', '_', source.stem)[:100] + '__' + source_hash[:8]
    folder = dest / stem
    folder.mkdir(exist_ok=False)
    y = rgb_to_y(rgb)
    meta = {'status': 'DEVELOPMENT_NOT_VALIDATED', 'source_name': source.name,
        'source_path': str(source.resolve()), 'source_sha256': source_hash,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'profile_sha256': config_hash(profile), 'profile': profile, 'environment': current,
        'exif': exif, 'capture_comparison': qc, 'sensor': info,
        'diagnostics': {'output_rgb_channel_fraction_at_65535': float(np.mean(rgb == 65535)),
                        'output_rgb_channel_fraction_at_0': float(np.mean(rgb == 0))},
        'limitations': ['No registration, perspective, lighting or focus correction.',
            'Fixed-reference WB is not an illuminant calibration.',
            'Metadata agreement is not proof of identical optical conditions.',
            'Linear TIFFs have no calibrated ICC/luminance guarantee. Preview is display-only.']}
    save_analysis(y, folder / 'Y_linear32.tif', {'profile_sha256': config_hash(profile),
        'source_sha256': source_hash, 'analysis': profile['analysis'], 'status': meta['status']})
    if save_rgb:
        tifffile.imwrite(folder / 'RGB_linear16.tif', rgb, photometric='rgb', metadata=None,
            description='Linear-light output using sRGB primaries; no nonlinear sRGB transfer curve; no ICC embedded. Not for quantitative display interpretation.')
        check = tifffile.imread(folder / 'RGB_linear16.tif')
        if check.dtype != np.uint16 or not np.array_equal(check, rgb):
            raise RuntimeError('RGB TIFF readback validation failed.')
    save_preview(y, folder / 'preview_DISPLAY_ONLY.png')
    meta['output_sha256'] = {p.name: sha256(p) for p in folder.iterdir() if p.is_file()}
    dump_json(folder / 'metadata.json', meta)
    return {'source_file': source.name, 'output_folder': str(folder), 'status': meta['status'],
            'metadata_check': qc['status'], 'missing_fields': ','.join(qc['missing_or_unchecked']),
            'profile_sha256': config_hash(profile), **{k: exif.get('tags', {}).get(k) for k in CRITICAL_TAGS}}

def process_batch(files: list[Path], output: Path, profile: dict, exiftool: str = '',
                  save_rgb: bool = True, log: Callable[[str], None] = print) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    run = output / ('run_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
    run.mkdir()
    dump_json(run / 'fixed_profile.json', profile)
    dump_json(run / 'runtime_environment.json', environment())
    rows = []
    for source in dict.fromkeys(files):
        try:
            log('转换 '+source.name)
            row = process_one(source, run, profile, exiftool, save_rgb)
            log('已输出；元数据检查：'+row['metadata_check'])
        except Exception as exc:
            row = {'source_file': source.name, 'status': 'FAILED', 'error': str(exc)}
            log('失败 '+source.name+'：'+str(exc))
        rows.append(row)
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (run/'batch_summary.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            # Prevent text originating in filenames from becoming spreadsheet formulas.
            safe = {k: ("'"+v if isinstance(v,str) and v[:1] in ('=','+','-','@') else v) for k,v in row.items()}
            writer.writerow(safe)
    dump_json(run/'batch_summary.json', rows)
    return run
