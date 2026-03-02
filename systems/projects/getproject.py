from pathlib import Path
from procmottifx.systems.protos import schema_pb2 as sch
from guimottifx.utils.currentprj import CurrentPrj

def get_projectfile():
    """
        Projf: ProjectFile
        Binary_File: PathFile
    """
    # if not CurrentPrj.pathfile: return
    binary_file = Path(CurrentPrj.pathfile)
    projf = sch.ProjectFile()
    projf.ParseFromString(binary_file.read_bytes())

    return projf,binary_file

def get_project():
    """
    Result : List Array Project,Asset,Composition
    """
    if not CurrentPrj.pathfile: return
    projf,_ = get_projectfile()

    proj = projf.project

    return proj

def get_asset(data):
    """
    Result : Array Asset
    """
    if not CurrentPrj.pathfile: return
    projf,_ = get_projectfile()

    asset = next(a for a in projf.assets if a.uid == data["uid"])

    return asset

def get_effect(layer):
    """
    Result : List Array Effect And Can Get Variables
    """
    eff = layer.effects

    return eff
