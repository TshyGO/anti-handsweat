import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import tifffile
from pipeline import rgb_to_y,mean_abs_diff,save_analysis,compare_capture,CRITICAL_TAGS

class NumericalTests(unittest.TestCase):
    def test_identical(self):
        a=np.full((10,10),0.25,dtype=np.float32)
        self.assertEqual(mean_abs_diff(a,a)[1],0.0)
    def test_known_local_change(self):
        a=np.full((10,10),0.25,dtype=np.float32);b=a.copy();b[:5,:5]+=0.125
        self.assertEqual(mean_abs_diff(a,b)[1],0.03125)
    def test_signed_changes_do_not_cancel(self):
        a=np.array([[1000,1000]],dtype=np.uint16);b=np.array([[1040,960]],dtype=np.uint16)
        self.assertEqual(mean_abs_diff(a,b)[1],40.0)
    def test_roi_is_fixed(self):
        a=np.zeros((10,10),np.float32);b=a.copy();b[:5,:5]=0.125
        self.assertEqual(mean_abs_diff(a,b,(0,0,5,5))[1],0.125)
    def test_invalid_roi(self):
        a=np.zeros((10,10),np.float32)
        with self.assertRaises(ValueError):mean_abs_diff(a,a,(9,9,2,2))
    def test_shapes(self):
        with self.assertRaises(ValueError):mean_abs_diff(np.zeros((10,10)),np.zeros((5,5)))
    def test_nan_rejected(self):
        a=np.array([[np.nan]],dtype=np.float32)
        with self.assertRaises(ValueError):mean_abs_diff(a,a)
    def test_y_scaling(self):
        rgb=np.full((3,4,3),65535,dtype=np.uint16);y=rgb_to_y(rgb)
        self.assertEqual(y.dtype,np.dtype('float32'));np.testing.assert_allclose(y,1,atol=1e-7)
        rgb=np.zeros((1,1,3),dtype=np.uint16);rgb[...,0]=65535
        self.assertAlmostEqual(float(rgb_to_y(rgb)[0,0]),0.2126,places=6)
    def test_tiff_roundtrip(self):
        a=np.array([[0,0.00123],[0.25,0.9]],dtype=np.float32)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.tif';save_analysis(a,p,{'synthetic':True})
            np.testing.assert_array_equal(tifffile.imread(p),a)
    def test_missing_metadata_not_passed(self):
        self.assertEqual(compare_capture({'tags':{}},{'tags':{}})['status'],'incomplete')
    def test_exposure_change_flagged(self):
        a={'tags':{k:'x' for k in CRITICAL_TAGS}};b=json.loads(json.dumps(a))
        a['tags']['ISO']=100;b['tags']['ISO']=400
        self.assertEqual(compare_capture(a,b)['status'],'mismatch')
    def test_demo_matches_known_values(self):
        folder=Path(__file__).resolve().parents[1]/'demo'
        expected=json.loads((folder/'expected_values.json').read_text())
        clean=tifffile.imread(folder/expected['baseline'])
        for name,value in expected['V_full_image'].items():
            self.assertAlmostEqual(mean_abs_diff(clean,tifffile.imread(folder/name))[1],value,places=10)

if __name__=='__main__':unittest.main()
