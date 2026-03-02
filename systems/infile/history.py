import os
import shutil

from guimottifx.utils.currentprj import CurrentPrj,UndoRedo

CACHE_FOLDER = "cache"

def make_cache() -> None:
    os.makedirs(name=f"{CurrentPrj.folderfile}/history",exist_ok=True)
    # print("succes")


def get_history(af_udp:str) -> None:
    print(CurrentPrj.index_history)
    list_of_file = [x for x in os.listdir(f"{CurrentPrj.folderfile}/history") if x.endswith(".mpj")]
    
    if len(list_of_file) == 1 or len(list_of_file) == 0:
        return            

    get_file = f"{CurrentPrj.folderfile}/history/{CurrentPrj.index_history}_{CurrentPrj.namefile}_{af_udp}.mpj"

    shutil.copy2(get_file,dst=CurrentPrj.pathfile)


def make_history(new_history) -> None:
    make_cache()
    path_his = f"{CurrentPrj.folderfile}/history/{CurrentPrj.index_history}_{CurrentPrj.namefile}_{CurrentPrj.fl_updhistory}.mpj"
    get_total_history = [a for a in os.listdir(f"{CurrentPrj.folderfile}/history") if a.endswith(".mpj")]

    if os.path.exists(path_his):
        CurrentPrj.index_history += 1
        path_his = f"{CurrentPrj.folderfile}/history/{CurrentPrj.index_history}_{CurrentPrj.namefile}_{new_history}.mpj"

    if os.path.exists(path_his):
        for x in get_total_history[CurrentPrj.index_history:]:
            os.remove(f"{CurrentPrj.folderfile}/history/{x}")

    CurrentPrj.fl_updhistory = new_history
    UndoRedo.same_redo = 0
    UndoRedo.same_undo = 0
    shutil.copy2(CurrentPrj.pathfile,dst=path_his)
    print(CurrentPrj.index_history)

def del_allhistory() -> None:
    folder = f"{CurrentPrj.folderfile}/history"
    if os.path.exists(folder):
        shutil.rmtree(folder)
    else: print("nope")
