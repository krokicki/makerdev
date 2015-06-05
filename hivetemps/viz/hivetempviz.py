#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 4D Volume Gradient 
# Author: Konrad Rokicki
#
import sys
import time
from numpy import *
import scipy 
import scipy.interpolate 
import scipy.ndimage 
import pandas as pd
import vtk

levels = 5
sdim = (100, 250, 100)
vdim = (250, 250, 250)
offsets = ((vdim[0]-sdim[0])/2.0, (vdim[1]-sdim[1])/2.0, (vdim[2]-sdim[2])/2.0)
hw = vdim[1]/2
zoom_factor = 50
main_ren_pct = 7
m = scipy.interpolate.interp1d([0,40],[0,255])
vol = zeros(vdim, dtype=uint8)
textActor = None
offscreen = False
outDir = "out"

level_probes = [None] * levels
for li in range(0,levels):
    level_probes[li] = ["T%i"%i for i in range(li*4+1,li*4+5)]

def getSensorVolume(df, row):
    if row>=df.shape[0]: return None
    vol = zeros((2, 5, 2))
    dateTxt = None
    tempTxt = ""
    for li in range(0,5):
        df2 = df.ix[row, level_probes[li]]
        v = df2.values
        vol[1][li][0] = v[0]
        vol[0][li][0] = v[1]
        vol[0][li][1] = v[2]
        vol[1][li][1] = v[3]
        dateTxt = str(df2.name)
        if li>0: tempTxt += "\n\n"
        tempTxt += "%2.2f %2.2f %2.2f %2.2f" % (v[0],v[1],v[2],v[3])

    global textActor
    (currDate,currTime) = dateTxt.split(" ")
    textActor.SetInput("Makerdev\nApicultural Telemetry\n\nHive: Janelia 1\n\nDate: "+currDate+"\n\nTime: "+currTime+"\n\n\nTemperatures:\n(Celcius)\n\n"+tempTxt)
    global m
    alpha = m(vol)
    start_time = time.time()
    zoomed = scipy.ndimage.zoom(alpha, zoom_factor, order=2)
    elapsed_time = time.time() - start_time
    #print "Zoom took %2.2f sec"%(elapsed_time)
    return zoomed

def getIntensityVolume(df, row):
    svol = getSensorVolume(df, row)
    if svol is None: return None
    global vol
    # Pad sensor data into a cube shape for rendering
    (x,y,z) = offsets
    vol[x:x+sdim[0], y:y+sdim[1], z:z+sdim[2]] = svol
    vol[x:x+sdim[0], y:y+2, z:z+sdim[2]] = 255
    return vol

filepath = sys.argv[1]
print "Loading data from %s"%filepath
probe_names = [ "T%i"%i for i in range(1,21) ]
col_names = ['Date','Time','Voltage','Charge','IsCharging','TEnclosure']
col_names += probe_names
dateparse = lambda x,y: pd.datetime.strptime("%s %s"%(x,y), '%Y/%m/%d %H:%M:%S')
df = pd.read_csv(filepath, sep=',', names=col_names, index_col='Timestamp',
                    parse_dates={'Timestamp': ['Date', 'Time']}, date_parser=dateparse)

print "Transforming"

# Replace bad values with zeros
df = df.replace(to_replace=-127, value=0)
df = df.replace(to_replace=0, value=0)
df = df.replace(to_replace=85, value=0)

# Relabel probes for consistent topology
df.rename(columns={'T16': 'T_13', 'T13': 'T_14', 'T14': 'T_15', 'T15': 'T_16'}, inplace=True)
df.rename(columns={'T_13': 'T13', 'T_14': 'T14', 'T_15': 'T15', 'T_16': 'T16'}, inplace=True)

print "Rendering %d frames" % df.shape[0]

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
 
# Alpha transfer function
alphaChannelFunc = vtk.vtkPiecewiseFunction()
alphaChannelFunc.AddPoint(0, 0.0)
alphaChannelFunc.AddPoint(140, 0.0)
alphaChannelFunc.AddPoint(220, 0.05)
alphaChannelFunc.AddPoint(254, 0.5)
alphaChannelFunc.AddPoint(255, 0.0)
 
# Color transfer function
colorFunc = vtk.vtkColorTransferFunction()
colorFunc.AddRGBPoint(0, 0.0, 0.0, 1.0)
colorFunc.AddRGBPoint(140, 0.0, 1.0, 0.0)
colorFunc.AddRGBPoint(180, 1.0, 1.0, 0.0)
colorFunc.AddRGBPoint(255, 1.0, 0.0, 0.0)
 
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
textActor.SetDisplayPosition(20,100)
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
    if frame % 2: return
    transform = vtk.vtkTransform()
    transform.PostMultiply()
    transform.Translate(-1*hw,-1*hw,-1*hw)
    global r
    transform.RotateWXYZ(r,0,1,0)
    r += 1
    if r >= 360: r = 0
    transform.Translate(hw,hw,hw)
    volume.SetUserTransform(transform)
    outlineActor.SetUserTransform(transform)

class vtkTimerCallback():
    def __init__(self):
        self.frame = 0
        
    def execute(self,obj,event):
        camera = mainRenderer.GetActiveCamera()
        updateData(self.frame)
        #updateTransforms(self.frame)
        self.frame += 20
        obj.GetRenderWindow().Render()

if offscreen:
    i = 0
    start_time = time.time()
    while updateData(i):
        elapsed_time = time.time() - start_time
        print "Loading data took %2.2f sec"%(elapsed_time)
        start_time = time.time()
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
        print "Writing %s took %2.2f sec"%(filename,elapsed_time)
        start_time = time.time()
        if i>10: break

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
    timerId = renderInteractor.CreateRepeatingTimer(1000);
    renderInteractor.Start()

