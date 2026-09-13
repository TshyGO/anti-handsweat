// Coating-image development macro V0.1.
// Inputs: already aligned, finite, single-channel 32-bit Y TIFFs on one common scale.
// No alignment, threshold, image-area score, or automatic normalization is performed.
// Batch argument: cleanPath|changedPath|outputDir|x|y|width|height
requires("1.53h");
arg=getArgument();
interactive=(lengthOf(arg)==0);
if (interactive) {
    showMessage("Before measuring", "Use aligned Y_linear32.tif files only.\nNo automatic alignment or lighting correction is performed.\nFor wiping, ROI must cover the complete wiping path.\nA small V does not prove removal of contaminant mass.");
    clean=File.openDialog("Select CLEAN Y TIFF");
    changed=File.openDialog("Select PRINT or WIPED Y TIFF");
    out=getDirectory("Choose an output folder");
} else {
    parts=split(arg,"|");
    if(parts.length!=7) exit("Expected 7 arguments separated by |");
    clean=parts[0];changed=parts[1];out=parts[2];
    x=parseInt(parts[3]);y=parseInt(parts[4]);rw=parseInt(parts[5]);rh=parseInt(parts[6]);
}
if(!File.exists(clean)||!File.exists(changed)) exit("Input file missing.");
if(!endsWith(out,"/")&&!endsWith(out,"\\")) out=out+"/";
if(!File.isDirectory(out)) File.makeDirectory(out);
runDir=out+"difference_"+d2s(getTime(),0)+"/";
File.makeDirectory(runDir);
open(clean);id0=getImageID();getDimensions(w0,h0,c0,z0,t0);
if(bitDepth!=32||c0!=1||z0!=1||t0!=1) exit("Clean input must be one single-channel 32-bit image.");
resetThreshold();run("Select None");
getRawStatistics(ni,mi,lo,hi);
if(isNaN(mi)||ni!=w0*h0||lo<0||hi>1.00001) exit("Clean input must contain finite normalized Y values.");
if(interactive){
    Dialog.create("Fixed rectangle ROI (pixel coordinates)");
    Dialog.addMessage("Enter the same predetermined ROI for every image in this comparison.\nFor the demo, keep x=0, y=0 and the full image size.");
    Dialog.addNumber("x",0);Dialog.addNumber("y",0);
    Dialog.addNumber("width",w0);Dialog.addNumber("height",h0);
    Dialog.addCheckbox("I checked alignment, common scale and ROI coverage",false);
    Dialog.show();
    x=Dialog.getNumber();y=Dialog.getNumber();rw=Dialog.getNumber();rh=Dialog.getNumber();
    if(!Dialog.getCheckbox()) exit("Confirm alignment and ROI coverage first.");
}
if(x<0||y<0||rw<=0||rh<=0||x+rw>w0||y+rh>h0||x!=floor(x)||y!=floor(y)||rw!=floor(rw)||rh!=floor(rh)) exit("Invalid integer-pixel ROI.");
open(changed);id1=getImageID();getDimensions(w1,h1,c1,z1,t1);
if(bitDepth!=32||c1!=1||z1!=1||t1!=1||w0!=w1||h0!=h1) exit("Inputs must have identical dimensions and be single-channel float32.");
resetThreshold();run("Select None");
getRawStatistics(ni,mi,lo,hi);
if(isNaN(mi)||ni!=w1*h1||lo<0||hi>1.00001) exit("Changed input must contain finite normalized Y values.");
imageCalculator("Difference create 32-bit",id0,id1);
diffID=getImageID();rename("Absolute_difference");resetThreshold();
makeRectangle(x,y,rw,rh);
getRawStatistics(n,v,minVal,maxVal,sd);
if(isNaN(v)||v<0||v>1.00001||n!=rw*rh) exit("Non-finite pixels or an incomplete ROI were found.");
setMinAndMax(0,1); // Display range only: no pixel rescaling.
saveAs("Tiff",runDir+"difference_float32.tif");
saveAs("Selection",runDir+"analysis_roi.roi");
csv="V_mean_absolute_difference,roi_x_px,roi_y_px,roi_width_px,roi_height_px,pixel_count,ImageJ_version\n";
csv=csv+d2s(v,12)+","+x+","+y+","+rw+","+rh+","+n+","+getVersion()+"\n";
File.saveString(csv,runDir+"metrics.csv");
record="STATUS: DEVELOPMENT_NOT_VALIDATED\nclean="+clean+"\nchanged="+changed+"\n";
record=record+"clean_sha256="+IJ.checksum("SHA-256 file",clean)+"\nchanged_sha256="+IJ.checksum("SHA-256 file",changed)+"\n";
record=record+"ROI="+x+","+y+","+rw+","+rh+"\nImageJ="+getVersion()+"\nV="+d2s(v,12)+"\n";
record=record+"No alignment, no automatic intensity normalization, no threshold.\n";
record=record+"V is an image-code change, not CIE L*, physical luminance or contaminant mass.\n";
File.saveString(record,runDir+"record.txt");
print("V="+d2s(v,12)+"; saved to "+runDir);
if(interactive) showMessage("Complete", "V = "+d2s(v,9)+"\nSaved to:\n"+runDir+"\nKeep original photos and check the complete difference image.");
