import json
from datetime import datetime
import os
INFO_FILE = "recent.json"

def makeinfo(data):
    entry = {
        "namefile": data["name"],
        "pathfile": data["path"],
        "folderfile": data["folder"],
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r",encoding="utf-8") as f:
            infos = json.load(f)
    else:
        infos = []
        
    infos.append(entry)
    with open(INFO_FILE,"w",encoding="utf-8") as f:
        json.dump(infos,f,indent=4)

def loadinfo():
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE,"r",encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data,dict):
                data = [data]
            return data
    return []

def updinfo(fileprj):
    with open(INFO_FILE,"r",encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in data:
        if item["pathfile"] == fileprj:
            item["datetime"] = now
            break
    
    with open(INFO_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=4)

def delinfo(indexprj):
    with open(INFO_FILE,"r",encoding="utf-8") as f:
        data = json.load(f)
    del data[indexprj]
    with open(INFO_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=4)