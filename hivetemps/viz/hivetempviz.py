#!/usr/bin/env python
#
# 4D Volume Gradient Movie Generator
# 
# Author: Konrad Rokicki
#
import sys
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
fixed_rotation = 45
m = scipy.interpolate.interp1d([0,40],[0,255])
vol = zeros(vdim, dtype=uint8)
textActor = None

level_probes = [None] * levels
for li in range(0,levels):
    level_probes[li] = ["T%i"%i for i in range(li*4+1,li*4+5)]

def getSensorVolume(df, row):
    vol = zeros((2, 5, 2))
    dateTxt = None
    for li in range(0,5):
        df2 = df.ix[row, level_probes[li]]
        v = df2.values
        vol[1][li][0] = v[0]
        vol[0][li][0] = v[1]
        vol[0][li][1] = v[2]
        vol[1][li][1] = v[3]
        dateTxt = str(df2.name)

    global textActor
    textActor.SetInput(dateTxt)
    global m
    alpha = m(vol)
    zoomed = scipy.ndimage.zoom(alpha, zoom_factor)
    return zoomed

def getIntensityVolume(df, row):
    svol = getSensorVolume(df, row)
    global vol
    # Pad sensor data into a cube shape for rendering
    (x,y,z) = offsets
    vol[x:x+sdim[0], y:y+sdim[1], z:z+sdim[2]] = svol
    vol[x:x+sdim[0], y:y+2, z:z+sdim[2]] = 255
    return vol


print "Loading data"

filepath = "/Users/rokickik/Dropbox/MakerDev/BeeMonitor/2015-03/201405-201503.log"
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

df2 = df.ix[:, probe_names]
#df2 = df2.resample('1D', how='mean')
#df2 = df2.ix['2014-06-02':'2014-06-02']

print "Rendering"

# Import data into VTK format
dataImporter = vtk.vtkImageImport()
dataImporter.SetDataScalarTypeToUnsignedChar()
dataImporter.SetDataExtent(0, vdim[0]-1, 0, vdim[1]-1, 0, vdim[2]-1)
dataImporter.SetWholeExtent(0, vdim[0]-1, 0, vdim[1]-1, 0, vdim[2]-1)

i = 0
def updateData():
    global i
    data_string = getIntensityVolume(df2, i).tostring()
    dataImporter.CopyImportVoidPointer(data_string, len(data_string))
    i += 10

# Just intensity values
dataImporter.SetNumberOfScalarComponents(1)
 
# Alpha transfer function
alphaChannelFunc = vtk.vtkPiecewiseFunction()
alphaChannelFunc.AddPoint(0, 0.0)
alphaChannelFunc.AddPoint(140, 0.0)
alphaChannelFunc.AddPoint(220, 0.05)
alphaChannelFunc.AddPoint(254, 0.5)
alphaChannelFunc.AddPoint(255, 1.0)
 
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
 
renderer = vtk.vtkRenderer()
renderWin = vtk.vtkRenderWindow()
renderWin.AddRenderer(renderer)
renderInteractor = vtk.vtkRenderWindowInteractor()
renderInteractor.SetRenderWindow(renderWin)

textActor = vtk.vtkTextActor()
txtprop = textActor.GetTextProperty()
txtprop.SetFontFamilyToArial()
txtprop.SetFontSize(18)
txtprop.SetColor(0.8,0.8,0.8)
textActor.SetDisplayPosition(40,560)
renderer.AddActor2D(textActor)

#camera = vtk.vtkCamera()
# default (125.0, 124.5, 1199.9110460037089) 
#camera.SetPosition(70, 70, 900)
# default (125.0, 124.5, 124.29289321881348)
#camera.SetFocalPoint(120, 120, 120)
 
#renderer.SetActiveCamera(camera)
renderer.AddVolume(volume)
renderer.SetBackground(0,0,0)
renderWin.SetSize(800, 600)

cube = vtk.vtkCubeSource()
(x,y,z) = offsets
print "sdim:",sdim
print "vdim:",vdim
print "offsets:",offsets
cube.SetBounds(x,x+sdim[0],y,y+sdim[1],z,z+sdim[2])
cube.Update()

outline = vtk.vtkOutlineFilter()
mapper2 = vtk.vtkPolyDataMapper()
outline.SetInputConnection(cube.GetOutputPort())
mapper2.SetInputConnection(outline.GetOutputPort())
outlineActor = vtk.vtkActor()
outlineActor.SetMapper(mapper2)
#outlineActor.GetProperty().SetRepresentationToWireframe()
renderer.AddActor(outlineActor)

if False and fixed_rotation:
    transform = vtk.vtkTransform()
    transform.PostMultiply()
    transform.Translate(-1*hw,-1*hw,-1*hw)
    transform.RotateWXYZ(90,0,0,1)
    transform.RotateWXYZ(fixed_rotation,0,1,0)
    transform.Translate(hw,hw,hw)
    volume.SetUserTransform(transform)
    outlineActor.SetUserTransform(transform)

# A simple function to be called when the user decides to quit the application.
def exitCheck(obj, event):
    if obj.GetEventPending() != 0:
        obj.SetAbortRender(1)
 
renderWin.AddObserver("AbortCheckEvent", exitCheck)


class vtkTimerCallback():
    def __init__(self):
        self.r = 0
        
    def execute(self,obj,event):

        camera = renderer.GetActiveCamera()
        #print camera.GetPosition(), camera.GetFocalPoint()
        #camera.Yaw(self.r)
        #self.r += 1
        
        if not(fixed_rotation):
            transform = vtk.vtkTransform()
            transform.PostMultiply()
            transform.Translate(-1*hw,-1*hw,-1*hw)
            transform.RotateWXYZ(90,0,0,1)
            transform.RotateWXYZ(self.r,0,1,0)
            self.r += 1
            if self.r >= 360: self.r = 0
            transform.Translate(hw,hw,hw)
            volume.SetUserTransform(transform)
            outlineActor.SetUserTransform(transform)

        updateData()
        obj.GetRenderWindow().Render()

renderInteractor.Initialize()
# Because nothing will be rendered without any input, we order the first render manually before control is handed over to the main-loop.
updateData()
renderWin.Render()

# Sign up to receive TimerEvent
cb = vtkTimerCallback()
renderInteractor.AddObserver('TimerEvent', cb.execute)
timerId = renderInteractor.CreateRepeatingTimer(1000);

renderInteractor.Start()

