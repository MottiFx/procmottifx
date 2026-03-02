from pathlib import Path
from procmottifx.systems.projects.getproject import get_projectfile
from procmottifx.systems.protos import schema_pb2 as sch
from guimottifx.utils.currentprj import CurrentPrj


def upd_project(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()


    proj = projf.project
    for key,val in data.items():
        if key == "name":
            proj.name = val
        elif key == "fps":
            proj.fps = val
        elif key == "width":
            proj.width = val
        elif key == "height":
            proj.height = val
        elif key == "duration":
            proj.duration = val

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def upd_color_label(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    _color_label = next(cl for cl in projf.color_label if cl.uid == data["uid_cl"])

    for key,val in data.items():
        if key == "name":
            _color_label.name = val
        elif key == "value":
            _color_label.value = val
    
    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)


def upd_layer(data):
    projf,binary_file = get_projectfile()

    layer = next(l for l in projf.layers if l.uid == data["uid_l"])

    for key,val in data.items():
        if key == "order":
            layer.order = val
        elif key == "duration":
            layer.duration = val
        elif key == "start":
            layer.start = val
        elif key == "end":
            layer.end = val
        elif key == "realstart":
            layer.realstart = val
        elif key == "realend":
            layer.realend = val
        elif key == "visible":
            layer.visible = val
        elif key == "name":
            layer.name = val
        elif key == "color":
            layer.colors = val
        
    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def upd_effect(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    layer = next(l for l in projf.layers if l.uid == data["uid_l"])
    effect = next(e for e in layer.effects if e.uid == data["uid_e"])

    for key,val in data.items():
        if key == "order":
            effect.order = val
        elif key == "hide":
            effect.hide = val
    
    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def upd_value(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    layer = next(l for l in projf.layers if l.uid == data["uid_l"])
    effect = next(e for e in layer.effects if e.uid == data["uid_e"])
    varb = next(v for v in effect.variables if v.uid == data["uid_vrb"])

    for key,val in data.items():
        if key == "value":
            varb.value = val

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

