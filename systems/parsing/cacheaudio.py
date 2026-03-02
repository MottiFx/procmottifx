import math
import os
from pathlib import Path
import shutil
import threading
from typing import Any
import lz4.frame
import lz4
from guimottifx.utils.configediting import ConfigTimeLine
from guimottifx.utils.currentprj import CurrentPrj

FOLDER_CHCAUD = "_chcaud"

def add_chcaud(buff: bytes,frameidx: int) -> None:
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCAUD}"
    os.makedirs(folder,exist_ok=True)
    files = Path(f"{folder}/{frameidx}.chaud")
    bytescompres = lz4.frame.compress(buff,compression_level=9)

    files.write_bytes(bytescompres)
 
def run_removchaud(lastpos,newpos):
    main: threading.Thread = threading.Thread(target=remove_chcaud,daemon=True,args=(lastpos,newpos))
    
    main.start()

def remove_chcaud(lastpos,newpos):
    listframe = list_chcaud()

    # floor dan ceil cocok untuk menghitung kemungkinan
    start = int(math.floor(lastpos * ConfigTimeLine.FPS))
    end = int(math.ceil(newpos * ConfigTimeLine.FPS))
    
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCAUD}"

    for i in range(start,end + 1):
        _ckframe = next((True for lf in listframe if i == int(lf.split(".")[0])),False)
        if not _ckframe: continue
        os.remove(f"{folder}/{i}.chaud")
        
def delall_chcaud():
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCAUD}"
    if os.path.exists(folder): shutil.rmtree(folder)

def get_chcaud(frameidx: int) -> Any:
    conf = CurrentPrj
    files = Path(f"{conf.folderfile}/{FOLDER_CHCAUD}/{frameidx}.chaud")
    bytload = files.read_bytes()
    return lz4.frame.decompress(bytload)

def list_chcaud() -> list[str] | list:
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCAUD}/"
    check = os.path.exists(folder)

    if check:
        return os.listdir(folder)
    else: return []