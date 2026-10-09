"""Render isometric preview of ACTUAL 3D GLB export, via offscreen VTK."""
from pathlib import Path
import json
import numpy as np
import trimesh
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).parent
base=HERE/'build'/'GPT-DOUG-PINEAL-3D'
model=trimesh.load(str(base)+'.glb',force='scene')
manifest=json.loads(Path(str(base)+'.json').read_text())
colors={k:tuple(x['rgb']) for k,x in manifest['layers'].items()}

def get_layer(name):
    up=name.upper()
    for prefix,layer in [
        ('FOUNDATION','FOUNDATION'),('PINEAL','PINEAL-CORE'),
        ('GPU','GPU-LLM'),('ONTOLOGY','ONTOLOGY-MEMORY'),('MEMORY','ONTOLOGY-MEMORY'),
        ('SYMBOLICCELL','CELL-ATLAS'),('CELL_','CELL-ATLAS'),
        ('RESEARCH','NEURAL-RESEARCH'),('KRAKEN','KRAKEN-CONDUITS'),
        ('ZYRA','ZYRA-SHIELD'),('PATENT','PATENT-NETWORK')]:
        if up.startswith(prefix): return layer
    raise ValueError(up)

ren=vtk.vtkRenderer()
ren.SetBackground(.02,.045,.075)
ren.SetBackground2(.075,.115,.15)
ren.GradientBackgroundOn()
ren.SetUseDepthPeeling(True)
win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1240,870);win.SetAlphaBitPlanes(1);win.SetMultiSamples(0);win.AddRenderer(ren)
for name,mesh in model.geometry.items():
    v=np.asarray(mesh.vertices,dtype=np.float32)
    f=np.asarray(mesh.faces,dtype=np.int64)
    pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(v,deep=True))
    polys=vtk.vtkCellArray()
    offsets=numpy_to_vtkIdTypeArray(np.arange(len(f)+1,dtype=np.int64)*3,deep=True)
    conn=numpy_to_vtkIdTypeArray(f.reshape(-1),deep=True)
    polys.SetData(offsets,conn)
    poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(polys)
    normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SplittingOff();normals.SetFeatureAngle(75);normals.Update()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());mapper.ScalarVisibilityOff()
    actor=vtk.vtkActor();actor.SetMapper(mapper)
    layer=get_layer(name)
    rgb=colors[layer]
    prop=actor.GetProperty()
    prop.SetColor(*[x/255 for x in rgb])
    prop.SetAmbient(.17);prop.SetDiffuse(.8);prop.SetSpecular(.23);prop.SetSpecularPower(28)
    prop.SetOpacity(.30 if layer=='ZYRA-SHIELD' else (.82 if layer=='FOUNDATION' else 1.0))
    ren.AddActor(actor)

kit=vtk.vtkLightKit();kit.SetKeyLightIntensity(.9);kit.SetKeyToFillRatio(2.0);kit.AddLightsToRenderer(ren)
cam=ren.GetActiveCamera()
cam.SetFocalPoint(0,0,34)
cam.SetPosition(260,-340,220)
cam.SetViewUp(0,0,1)
cam.ParallelProjectionOn()
cam.SetParallelScale(115)
ren.SetUseDepthPeeling(True)
ren.SetMaximumNumberOfPeels(40)
ren.SetOcclusionRatio(0.15)
win.Render()
cap=vtk.vtkWindowToImageFilter();cap.SetInput(win);cap.ReadFrontBufferOff();cap.Update()
writer=vtk.vtkPNGWriter();writer.SetFileName(str(base)+'-RAW.png');writer.SetInputConnection(cap.GetOutputPort());writer.Write()

# Add labels only after rendering. Geometry and color come from actual meshes.
raw=Image.open(str(base)+'-RAW.png').convert('RGBA')
W,H=1620,950
canvas=Image.new('RGB',(W,H),(4,12,24));canvas.paste(raw,(12,62),raw)
draw=ImageDraw.Draw(canvas)
regular='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
f=lambda n,b=False: ImageFont.truetype(bold if b else regular,n)
draw.text((28,16),'GPT-DOUG-PINEAL // REAL 3D CAD MODEL',font=f(27,True),fill=(239,251,255))
draw.text((1268,102),'CAD LAYER EXPLORER',font=f(19,True),fill=(228,244,250))
for i,(layer,meta) in enumerate(manifest['layers'].items()):
    y=160+i*71
    draw.rounded_rectangle((1272,y,1290,y+22),3,fill=tuple(meta['rgb']))
    draw.text((1305,y),layer,font=f(14,True),fill=(236,248,253))
    draw.text((1305,y+27),str(meta['parts'])+' solid components',font=f(12),fill=(125,157,178))
draw.text((1268,828),'DXF / STEP / STL / GLB',font=f(14,True),fill=(185,232,248))
draw.text((1268,855),'102 real named BRep solids',font=f(12),fill=(122,174,194))
draw.text((1268,878),'Concept model | no brain I/O',font=f(11),fill=(122,174,194))
draw.text((28,917),'SOURCE: CADQUERY -> BREP STEP -> TESSELLATED 3D DXF / GLB',font=f(11),fill=(113,159,179))
name=str(base)+'-PREVIEW.png'
canvas.save(name)
print(name)
