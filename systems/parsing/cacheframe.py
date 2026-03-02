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

FOLDER_CHCFRM = "_chcfrm"

def add_chcfrm(buff: bytes,frameidx: int) -> None:
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCFRM}"
    os.makedirs(folder,exist_ok=True)
    files = Path(f"{folder}/{frameidx}.chfr")
    bytescompres = lz4.frame.compress(buff,compression_level=9)

    files.write_bytes(bytescompres)
 
def run_removch(lastpos,newpos):
    main: threading.Thread = threading.Thread(target=remove_chcfrm,daemon=True,args=(lastpos,newpos))
    
    main.start()

def remove_chcfrm(lastpos,newpos):
    # floor dan ceil cocok untuk menghitung kemungkinan
    start = int(math.floor(lastpos * ConfigTimeLine.FPS))
    end = int(math.ceil(newpos * ConfigTimeLine.FPS))
    
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCFRM}"

    for i in range(start,end + 1):
        filepath =f"{folder}/{i}.chfr" 
        if not os.path.exists(filepath): continue
        os.remove(filepath)
        
def delall_chcfrm():
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCFRM}"
    if os.path.exists(folder): shutil.rmtree(folder)

def get_chcfrm(frameidx: int) -> Any:
    conf = CurrentPrj
    files = Path(f"{conf.folderfile}/{FOLDER_CHCFRM}/{frameidx}.chfr")
    bytload = files.read_bytes()
    return lz4.frame.decompress(bytload)

def list_chcfrm() -> list[str] | list:
    conf = CurrentPrj
    folder = f"{conf.folderfile}/{FOLDER_CHCFRM}/"
    check = os.path.exists(folder)

    if check:
        return os.listdir(folder)
    else: return []