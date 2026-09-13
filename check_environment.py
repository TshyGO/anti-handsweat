"""Local installation diagnostics; no network traffic or photo access."""
from __future__ import annotations
import argparse
import importlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys
from platform_paths import discover_exiftool


def check() -> tuple[dict, bool]:
    result = {'status':'DEVELOPMENT_ENVIRONMENT_CHECK_ONLY', 'python':sys.version,
              'executable':sys.executable, 'platform':platform.platform(),
              'machine':platform.machine(), 'packages':{}, 'errors':[], 'warnings':[]}
    raw_version = '0.25.1' if sys.platform=='darwin' and platform.machine()=='x86_64' else '0.27.1'
    expected = {'rawpy':raw_version,'numpy':'2.3.5','tifffile':'2026.5.15','Pillow':'12.3.0'}
    if sys.version_info[:2] not in ((3,12),(3,13)):
        result['errors'].append('Use Python 3.12 or 3.13 for this package.')
    for name,version in expected.items():
        try:
            actual=importlib.metadata.version(name)
            importlib.import_module('PIL' if name=='Pillow' else name)
            result['packages'][name]={'installed':actual,'expected':version}
            if actual!=version: result['errors'].append(name+' version mismatch')
        except Exception as e: result['errors'].append(name+': '+str(e))
    try:
        import tkinter
        result['tk_version']=tkinter.TkVersion
    except Exception as e: result['errors'].append('Tkinter: '+str(e))
    try:
        import rawpy
        result['libraw_version']=list(rawpy.libraw_version)
        result['rawpy_flags']=dict(rawpy.flags)
        # Construct the exact parameter family before attempting a real RAW.
        rawpy.Params(demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                     gamma=(1,1),output_bps=16,no_auto_bright=True,
                     adjust_maximum_thr=0.0,bright=1.0,no_auto_scale=False,
                     use_camera_wb=False,use_auto_wb=False,user_wb=[1,1,1,1],
                     output_color=rawpy.ColorSpace.sRGB,user_flip=0,
                     highlight_mode=rawpy.HighlightMode.Clip,
                     fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                     noise_thr=None,median_filter_passes=0)
        result['rawpy_parameter_check']='constructed; no RAW decoded'
    except Exception as e: result['errors'].append('LibRaw / parameters: '+str(e))
    exe=discover_exiftool(root=Path(__file__).resolve().parent)
    result['exiftool']={'path':exe,'status':'not found'}
    if exe:
        try:
            p=subprocess.run([exe,'-ver'],capture_output=True,text=True,timeout=10,check=True)
            result['exiftool'].update(status='executable',version=p.stdout.strip())
        except Exception as e: result['warnings'].append('ExifTool: '+str(e))
    else: result['warnings'].append('ExifTool absent: metadata fields will be incomplete until installed.')
    result['notes']=['No real RAW, macOS GUI, calibration or measurement validity is verified by this diagnostic.']
    return result,not result['errors']


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args=parser.parse_args();result,ok=check()
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
    print(text)
    raise SystemExit(0 if ok else 1)
