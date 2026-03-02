from pathlib import Path
from procmottifx.systems.projects.getproject import get_projectfile
from procmottifx.systems.protos import schema_pb2 as sch
from libmottifx.compact.effect import LISTEFFECT
from guimottifx.utils.currentprj import CurrentPrj

def del_asset(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    asset_del = next(a for a, ass in enumerate(projf.assets) if ass.uid == data["uid_a"])

    del projf.assets[asset_del]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def del_layer(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    layer_del = next(i for i,lyr in enumerate(projf.layers) if lyr.uid == data["uid_l"])
    lyr_order = next(ly for ly in projf.layers if ly.uid == data["uid_l"])

    for lyr in projf.layers:
        if lyr.order >  lyr_order.order:
            lyr.order -= 1

    del projf.layers[layer_del]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def del_effect(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    layer = next(l for l in projf.layers if l.uid == data["uid_l"])
    effect_del,eff = next((i,eff) for i,eff in enumerate(layer.effects) if eff.uid == data["uid_e"])
    searchshader = next(fn for fn in LISTEFFECT if fn["typfx"] == eff.typfx)

    if searchshader["basic"]: return

    del layer.effects[effect_del]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)


def del_color(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    _color_label = next(cl for cl in projf.color_label if cl.uid == data["uid_cl"])

    del projf.color_label[_color_label]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

def del_beat(data):
    if not CurrentPrj.pathfile: return
    projf,binary_file = get_projectfile()

    _beat_line = next(bl for bl in projf.beat_time_line if bl.uid == data["uid_bl"])

    del projf.beat_time_line[_beat_line]

    to_binary = projf.SerializeToString()
    binary_file.write_bytes(to_binary)

    
