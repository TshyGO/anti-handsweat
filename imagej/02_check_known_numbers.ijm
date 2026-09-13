// Software arithmetic check only. Uses synthetic data, not experimental performance.
requires("1.53h");
setBatchMode(true);
newImage("clean_test", "32-bit black", 10, 10, 1);id0=getImageID();
run("Add...", "value=0.25");
run("Duplicate...", "title=changed_test");id1=getImageID();
makeRectangle(0,0,5,5);run("Add...", "value=0.125");run("Select None");
imageCalculator("Difference create 32-bit",id0,id1);
resetThreshold();run("Select None");
getRawStatistics(n,v);
if(abs(v-0.03125)>0.0000001) exit("FAILED. Expected V=0.03125, got "+v);
close();selectImage(id1);close();selectImage(id0);close();
setBatchMode(false);
showMessage("Arithmetic check", "Expected V=0.03125\nMeasured V="+d2s(v,9)+"\nPASS for synthetic arithmetic only.\nThis does not validate RAW decoding, camera calibration or real coatings.");
