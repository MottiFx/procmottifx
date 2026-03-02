import os
from pathlib import Path
from uuid import uuid4
from libmottifx.fx.audsfx import AudioSfx
from libmottifx.fx.basics.transform import TransformObj
from procmottifx.systems.projects.getproject import get_projectfile
from procmottifx.systems.protos import schema_pb2 as sch
from guimottifx.utils.currentprj import CurrentPrj

def create_project(data):
    """
    EXAMPLE:
        {
            var:val
        }
    """
    proj_file = sch.ProjectFile()
    proj = proj_file.project
    proj.name = data["name"]
    proj.fps = data["fps"]
    proj.width = data["width"]
    proj.height = data["height"]
    proj.duration = data["duration"]
    path_folder = data["folder"]
    to_binary = proj_file.SerializeToString()

    folder_ref = f"{path_folder}/{data["name"]}"
    os.makedirs(folder_ref,exist_ok=True)
    file_path = Path(f"{folder_ref}/{data["name"]}.mpj")
    file_path.write_bytes(to_binary)

def create_asset(data):
    """
    EXAMPLE:
        {
            var:val
        }
    """
    
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    asset = projf.assets.add()
    asset.uid = str(uuid4())
    asset.name = data["name"]
    asset.typass = data["typass"]
    asset.path = data["path"]
    asset.fps = data["fps"]
    asset.width = data["width"]
    asset.height = data["height"]
    asset.duration = data["duration"]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)


def create_layer(data):
    """
    EXAMPLE:
        {
            var:val
        }
    """

    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()
    count_layer = len(projf.layers)

    typlyr = None
    if data["typass"] == sch.TypAss.TYP_ASS_IMAGE: 
        typlyr = sch.TypLyr.TYP_LYR_IMAGE
    if data["typass"] == sch.TypAss.TYP_ASS_VIDEO:
        typlyr = sch.TypLyr.TYP_LYR_VIDEO
    if data["typass"] == sch.TypAss.TYP_ASS_FRAMES:
        typlyr = sch.TypLyr.TYP_LYR_FRAMES
    if data["typass"] == sch.TypAss.TYP_ASS_AUDIO:
        typlyr = sch.TypLyr.TYP_LYR_AUDIO

    _2DTRANSFORM = TransformObj()
    _AUDIOBASICS = AudioSfx()

    layer = projf.layers.add()
    layer.uid = str(uuid4())
    layer.name = f"{data["name"]}_{count_layer}"
    layer.order = count_layer
    layer.typlyr = typlyr
    layer.duration = data["duration"]
    layer.start = data["start"]
    layer.end = data["end"]
    layer.realstart = 0.
    layer.realend = data["duration"]
    layer.visible = data["visible"]
    layer.asset_uids = data["asset_uids"]
    layer.colors = data["color"]

    TYP = sch.TypLyr

    if typlyr != TYP.TYP_LYR_AUDIO:
        effect = layer.effects.add()
        effect.uid = str(uuid4())
        effect.order = 0
        effect.typfx = sch.TypFx.TYP_FX_TRANSFORM_2D
        for _transform in _2DTRANSFORM.add_data():
            varb = effect.variables.add()
            varb.uid = str(uuid4())
            varb.name = _transform["key"]
            varb.typvar = _transform["type"]
            varb.value = _transform["value"]

    if typlyr in  [TYP.TYP_LYR_AUDIO,TYP.TYP_LYR_VIDEO]:
        effect = layer.effects.add()
        effect.uid = str(uuid4())
        effect.order = 0 if TYP.TYP_LYR_AUDIO else 1
        effect.typfx = sch.TypFx.TYP_FX_BASICAUDIO
        for _audfx in _AUDIOBASICS.add_data():
            varb = effect.variables.add()
            varb.uid = str(uuid4())
            varb.name = _audfx["key"]
            varb.typvar = _audfx["type"]
            varb.value = _audfx["value"]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def create_beat(data):
    """
    EXAMPLE:
        {
            var:val
        }
    """

    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    _beat = projf.beat_time_line.add()
    _beat.uid = str(uuid4())
    _beat.second = data["second"]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def create_color_label(data):
    """
    EXAMPLE:
        {
            var:val
        }
    """

    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    _color_label = projf.color_label.add()
    _color_label.uid = str(uuid4())
    _color_label.name = data["name"]
    _color_label.value = data["value"]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)


def create_effect(data,progs):
    """
    EXAMPLE:
        {
            {
                var:val
            }
        }
    """
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    layers  = projf.layers
    target_layer = None

    for l in layers:
        if l.uid == data["uid_layer"]:
            target_layer = l
            break

    count_eff = len(target_layer.effects)

    effect = target_layer.effects.add()
    effect.uid = str(uuid4())
    effect.order = count_eff
    effect.typfx = data["typfx"]

    for prog in progs:
        uidv = str(uuid4())
        varb = effect.variables.add()
        varb.uid = uidv
        varb.name = prog["key"]
        varb.typvar = prog["type"]
        varb.value = prog["value"]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)
    
