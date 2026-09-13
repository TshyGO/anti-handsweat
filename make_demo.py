"""Generate explicitly synthetic, exactly specified TIFF inputs. Never real test data."""
from pathlib import Path
import numpy as np
from pipeline import save_analysis, save_preview, mean_abs_diff, dump_json

def main():
    out=Path(__file__).parent/'demo';out.mkdir(exist_ok=True)
    yy,xx=np.mgrid[:256,:256]
    clean=(0.25+xx/4096+yy/8192).astype(np.float32)
    items={'00_clean_Y.tif':clean,'01_identical_Y.tif':clean.copy()}
    a=clean.copy();a[96:160,96:160]+=0.125;items['02_local_change_Y.tif']=a
    a=clean.copy();a[64:192,64:192]+=0.03125;items['03_spread_same_mean_Y.tif']=a
    a=clean.copy();a[96:160,96:160]+=0.03125;items['04_reduced_change_Y.tif']=a
    items['05_global_drift_Y.tif']=clean+np.float32(0.03125)
    items['06_shifted_background_Y.tif']=np.roll(clean,3,axis=1)
    results={}
    for name,im in items.items():
        save_analysis(im,out/name,{'synthetic':True,'unit':'normalized_image_code','purpose':'software arithmetic only'})
        results[name]=mean_abs_diff(clean,im)[1]
    dump_json(out/'expected_values.json',{'synthetic':True,'baseline':'00_clean_Y.tif',
        'ROI':{'x':0,'y':0,'width':256,'height':256},'V_full_image':results,
        'notes':['Not physical fingerprints or measured coatings.',
                 '02 and 03 intentionally have equal mean absolute changes despite different changed regions.',
                 '05 and 06 show that illumination drift and misregistration also create a signal.']})
    print(results)
if __name__=='__main__':main()
