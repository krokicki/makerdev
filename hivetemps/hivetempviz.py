#!/home/rokickik/anaconda/bin/python
#
# 4D Volume Gradient
# Author: Konrad Rokicki
#
import os, errno
import sys
import time
import numpy as np
import scipy
import scipy.interpolate
import scipy.ndimage
import pandas as pd
import vtk

np.set_printoptions(threshold=np.nan)

def roundUp(v): return float(int(v*100)+1)/100
def roundDown(v): return float(int(v*100))/100

levels = 5
sdim = (100, 250, 100)
vdim = (250, 250, 250)
offsets = ((vdim[0]-sdim[0])/2.0, (vdim[1]-sdim[1])/2.0, (vdim[2]-sdim[2])/2.0)
hw = vdim[1]/2
zoom_factor = 50
main_ren_pct = 7
vol = np.zeros(vdim, dtype=np.uint8)
textActor = None
offscreen = False
calc_extents = None # extents calculated by actually interpolating all the data with splines
calculate_extents = False
static_time = None
rotate_every_nth_frame = 4

level_probes = [None] * levels
for li in range(0,levels):
    level_probes[li] = ["T%i"%i for i in range(li*4+1,li*4+5)]

def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def getSensorVolume(df, row):
    if row>=df.shape[0]: return None
    vol = np.zeros((2, 5, 2))
    dateTxt = None
    tempTxt = ""
    for li in range(0,5):
        df2 = df.ix[row, level_probes[li]]
        v = df2.values
        vi = levels-li-1 # vertical flip because y=0 is at the bottom of the screen
        vol[1][vi][0] = v[0]
        vol[0][vi][0] = v[1]
        vol[0][vi][1] = v[2]
        vol[1][vi][1] = v[3]
        dateTxt = str(df2.name)
        if li>0: tempTxt += "\n\n"
        tempTxt += "%2.2f %2.2f %2.2f %2.2f" % (v[0],v[1],v[2],v[3])

    global textActor
    if textActor:
        (currDate,currTime) = dateTxt.split(" ")
        if static_time: currTime = static_time
        textActor.SetInput("Makerdev\nApicultural Telemetry\n\nHive: Janelia 1\n\nDate: %s\n\nTime: %s\n\nFrame: %d\n\nTemperatures:\n(Celcius)\n\n%s"%(currDate,currTime,row,tempTxt))

    #zoomed = scipy.ndimage.zoom(alpha, 3, order=2)
    #with file("frame_%s.txt"%row, 'w') as outfile:
    #    outfile.write('# Temps ({0})\n'.format(vol.shape))
    #    for slice_2d in vol:
    #        np.savetxt(outfile, slice_2d, fmt='%-3.2f')
    #        outfile.write('# New slice\n')
    #    outfile.write('\n# Alphas ({0})\n'.format(alpha.shape))
    #    for slice_2d in alpha:
    #        np.savetxt(outfile, slice_2d, fmt='%-3.2f')
    #        outfile.write('# New slice\n')
    #    outfile.write('\n# Zoomed ({0})\n'.format(zoomed.shape))
    #    for slice_2d in zoomed:
    #        np.savetxt(outfile, slice_2d, fmt='%-3.2f')
    #        outfile.write('# New slice\n')

    zoomed = scipy.ndimage.zoom(vol, zoom_factor, order=2)

    if calculate_extents:
        amin = np.amin(zoomed)
        amax = np.amax(zoomed)
        if amin<calc_extents[0]: calc_extents[0]=amin
        if amax>calc_extents[1]: calc_extents[1]=amax

    return zoomed

def getIntensityVolume(df, row):

    svol = getSensorVolume(df, row)
    if svol is None: return None

    global m
    alpha = m(svol)

    global vol
    # Pad sensor data into a cube shape for rendering
    (x,y,z) = offsets
    vol[x:x+sdim[0], y:y+sdim[1], z:z+sdim[2]] = alpha
    # the "ground"
    #vol[x:x+sdim[0], y:y+2, z:z+sdim[2]] = 255
    return vol

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("inputFile", help="Input CSV file")
parser.add_argument("-o", "--outDir", help="Directory where to render offscreen frames")
parser.add_argument("-s", "--start", help="Start rendering at the given row", type=int)
parser.add_argument("-e", "--end", help="End rendering at the given row", type=int)
parser.add_argument("--min", help="Min value (if this isn't provided it will be calculated very slowly)", type=float)
parser.add_argument("--max", help="Max value (if this isn't provided it will be calculated very slowly)", type=float)
args = parser.parse_args()

filepath = args.inputFile
startFrame = args.start
endFrame = args.end
outDir = args.outDir
minValue = args.min
maxValue = args.max

if outDir:
    mkdirs(outDir)
    print "Will render frames to %s"%outDir
    offscreen = True

print "Loading data from %s"%filepath
probe_names = [ "T%i"%i for i in range(1,21) ]
col_names = ['Date','Time','Voltage','Charge','IsCharging','TEnclosure']
col_names += probe_names
dateparse = lambda x,y: pd.datetime.strptime("%s %s"%(x,y), '%Y/%m/%d %H:%M:%S')
df = pd.read_csv(filepath, sep=',', names=col_names, index_col='Timestamp',
                    parse_dates={'Timestamp': ['Date', 'Time']}, date_parser=dateparse)

print "Transforming data"

# Replace bad values with zeros
df = df.replace(to_replace=-127, value=0)
df = df.replace(to_replace=0, value=0)
df = df.replace(to_replace=85, value=0)

# Relabel probes for consistent topology
df.rename(columns={'T16': 'T_13', 'T13': 'T_14', 'T14': 'T_15', 'T15': 'T_16'}, inplace=True)
df.rename(columns={'T_13': 'T13', 'T_14': 'T14', 'T_15': 'T15', 'T_16': 'T16'}, inplace=True)

# Select required data

# All data. Use --min -21.20 --max 42.09
# Actually need --min -21.30 --max 42.09

# Daily 3-5am mean. Use --min 11.93 --max 36.82

# Daily 4-5am mean. Use --min -17.81 --max 36.85
#df = df.between_time('4:00','5:00').resample('D', how = 'mean')
#static_time = "Avg of 4am-5am"
#rotate_every_nth_frame = 2

# Daily mean
#df = df.resample('D', how = 'mean')
#static_time = "Daily Average"
#rotate_every_nth_frame = 2

# Get extents for interpolation
totalFrames = df.shape[0]
pv = df.ix[:,probe_names]
calc_extents = [ pv.min().min(), pv.max().max() ]
if not(minValue) or not(maxValue):
    print "Temperature value range: %2.2f - %2.2f" % tuple(calc_extents)
    print "Calculating true extents... this will take a long time!"
    calculate_extents = True
    for row in range(1,totalFrames):
        getSensorVolume(df, row)
        if row%100==0:
            print "Processed %d rows, current value range: %2.4f - %2.4f" % (row,calc_extents[0],calc_extents[1])
    print "In the future, you can use '--min %2.2f --max %2.2f' to skip the previous step." % (roundDown(calc_extents[0]), roundUp(calc_extents[1]))
    extents = (calc_extents[0], calc_extents[1])
else:
    extents = (minValue, maxValue)


print "Value range: %2.2f - %2.2f" % extents
m = scipy.interpolate.interp1d(extents, [0,255])

print "Total frames: %d" % totalFrames

if startFrame:
    print "Will start rendering at frame %d"%startFrame
else:
    startFrame = 0

if endFrame:
    print "Will end rendering at frame %d"%endFrame
else:
    endFrame = totalFrames-1

print "Rendering %d frames" % (endFrame-startFrame)

# Import data into VTK format
dataImporter = vtk.vtkImageImport()
dataImporter.SetDataScalarTypeToUnsignedChar()
dataImporter.SetDataExtent(0, vdim[0]-1, 0, vdim[1]-1, 0, vdim[2]-1)
dataImporter.SetWholeExtent(0, vdim[0]-1, 0, vdim[1]-1, 0, vdim[2]-1)

def updateData(row):
    ivol = getIntensityVolume(df, row)
    if ivol is None: return False
    data_string = ivol.tostring()
    dataImporter.CopyImportVoidPointer(data_string, len(data_string))
    return True

# Just intensity values
dataImporter.SetNumberOfScalarComponents(1)

if extents[0]>=0:
    # Mapping for a summer range (0 to 40)
    print "Using summer colormap"

    # Color transfer function
    colorFunc = vtk.vtkColorTransferFunction()
    colorFunc.AddRGBPoint(0, 0.0, 0.0, 1.0) # blue
    colorFunc.AddRGBPoint(140, 0.0, 1.0, 0.0) # green
    colorFunc.AddRGBPoint(180, 1.0, 1.0, 0.0) # orange
    colorFunc.AddRGBPoint(255, 1.0, 0.0, 0.0) # red

    # Alpha transfer function
    alphaChannelFunc = vtk.vtkPiecewiseFunction()
    alphaChannelFunc.AddPoint(0, 0.0)
    alphaChannelFunc.AddPoint(140, 0.005)
    alphaChannelFunc.AddPoint(180, 0.006)
    alphaChannelFunc.AddPoint(250, 0.1)
    alphaChannelFunc.AddPoint(255, 0.2)

else:
    # Mapping for a year-round range (-20 to 40)
    print "Using year colormap"

    # Color transfer function
    colorFunc = vtk.vtkColorTransferFunction()
    colorFunc.AddRGBPoint(0, 0.0, 0.0, 1.0) # blue
    colorFunc.AddRGBPoint(64, 0.0, 1.0, 0.0) # green
    colorFunc.AddRGBPoint(191, 1.0, 1.0, 0.0) # orange
    colorFunc.AddRGBPoint(255, 1.0, 0.0, 0.0) # red

    # Alpha transfer function
    alphaChannelFunc = vtk.vtkPiecewiseFunction()
    alphaChannelFunc.AddPoint(0, 0.0)
    alphaChannelFunc.AddPoint(64, 0.001)
    alphaChannelFunc.AddPoint(191, 0.006)
    alphaChannelFunc.AddPoint(250, 0.1)
    alphaChannelFunc.AddPoint(255, 0.5)


volumeProperty = vtk.vtkVolumeProperty()
volumeProperty.SetColor(colorFunc)
volumeProperty.SetScalarOpacity(alphaChannelFunc)
 
volumeMapper = vtk.vtkVolumeRayCastMapper()
volumeMapper.SetVolumeRayCastFunction(vtk.vtkVolumeRayCastCompositeFunction())
volumeMapper.SetInputConnection(dataImporter.GetOutputPort())
 
volume = vtk.vtkVolume()
volume.SetMapper(volumeMapper)
volume.SetProperty(volumeProperty)
 
renderWin = vtk.vtkRenderWindow()
renderWin.SetSize(800, 600)
if offscreen:
    print "Will render to PNG files"
    renderWin.SetOffScreenRendering(1)

mainRenderer = vtk.vtkRenderer()
renderWin.AddRenderer(mainRenderer)
mainRenderer.SetViewport(0.3,0,1,1)
mainRenderer.SetBackground(0,0,0)

textRenderer = vtk.vtkRenderer()
renderWin.AddRenderer(textRenderer)
textRenderer.SetViewport(0,0,0.3,1)
textRenderer.SetBackground(0.1,0.1,0.1)

textActor = vtk.vtkTextActor()
txtprop = textActor.GetTextProperty()
txtprop.SetFontFamilyToArial()
txtprop.SetFontSize(18)
txtprop.SetColor(0.8,0.8,0.8)
textActor.SetDisplayPosition(20,120)
textRenderer.AddActor2D(textActor)

camera = vtk.vtkCamera()
camera.SetPosition(vdim[0]/2, vdim[1]/2, 800)
camera.SetFocalPoint(vdim[0]/2, vdim[1]/2, vdim[2]/2)
mainRenderer.SetActiveCamera(camera)

mainRenderer.AddVolume(volume)

# Outline
cube = vtk.vtkCubeSource()
(x,y,z) = offsets
cube.SetBounds(x,x+sdim[0],y,y+sdim[1],z,z+sdim[2])
cube.Update()
outline = vtk.vtkOutlineFilter()
polyMapper = vtk.vtkPolyDataMapper()
outline.SetInputConnection(cube.GetOutputPort())
polyMapper.SetInputConnection(outline.GetOutputPort())
outlineActor = vtk.vtkActor()
outlineActor.SetMapper(polyMapper)
mainRenderer.AddActor(outlineActor)

r = 0
def updateTransforms(frame):
    global r
    nr = int(np.floor(frame/rotate_every_nth_frame)) % 360
    if r==nr: return
    r = nr
    transform = vtk.vtkTransform()
    transform.PostMultiply()
    transform.Translate(-1*hw,-1*hw,-1*hw)
    transform.RotateWXYZ(r,0,1,0)
    transform.Translate(hw,hw,hw)
    volume.SetUserTransform(transform)
    outlineActor.SetUserTransform(transform)

animationTimerId = None
class vtkTimerCallback():
    def __init__(self):
        self.frame = startFrame

    def execute(self,obj,event):
        if self.frame<=endFrame:
            updateData(self.frame)
            self.frame += 5
        obj.GetRenderWindow().Render()

if offscreen:
    i = startFrame
    start_time = time.time()
    while updateData(i):
        updateTransforms(i)
        renderWin.Render()
        windowToImageFilter = vtk.vtkWindowToImageFilter()
        windowToImageFilter.SetInput(renderWin)
        windowToImageFilter.Update()
        writer = vtk.vtkPNGWriter()
        filename = "%s/render_%06d.png"%(outDir,i)
        writer.SetFileName(filename)
        writer.SetInputConnection(windowToImageFilter.GetOutputPort())
        writer.Write()
        i+=1
        elapsed_time = time.time() - start_time
        print "Rendering %s took %2.2f sec"%(filename,elapsed_time)
        start_time = time.time()
        if i>endFrame: break

else:
    def exitCheck(obj, event):
        if obj.GetEventPending() != 0:
            obj.SetAbortRender(1)

    renderWin.AddObserver("AbortCheckEvent", exitCheck)

    renderInteractor = vtk.vtkRenderWindowInteractor()
    renderInteractor.SetRenderWindow(renderWin)
    renderInteractor.Initialize()

    updateData(0)
    renderWin.Render()

    cb = vtkTimerCallback()
    renderInteractor.AddObserver('TimerEvent', cb.execute)
    animationTimerId = renderInteractor.CreateRepeatingTimer(1000);
    renderInteractor.Start()

