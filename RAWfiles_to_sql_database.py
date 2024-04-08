#Script 1 : Create SQL database

#%%Import
from win32com.client import Dispatch
from win32com.client import VARIANT as variant 
from pathlib import Path
from pythoncom import VT_EMPTY, VT_UI8
import pandas as pd
import sqlite3
import os 
import time
from datetime import datetime as dt
from tqdm import tqdm

#%%Working directory and raw files
working_directory = "C:/Users/XXXX" # Change where you want to store det sql database file
os.chdir(working_directory)

#%%Class members
Detector_used = {"No device": -1, "MS": 0, "PDA": 1, "A/D": 2, "Analog":3, "UV": 4}
EmptyVariant = variant(VT_EMPTY, [])
detector_types = {0: "CID", 1: "PQD", 2: "ETD", 3: "HCD"}
MS_types = {0: "ITMS", 1: "TQMS", 2: "SQMS", 3: "TOFMS", 4: "FTMS", 5: "Magnetic sector"}
Sample_types = {0: "Sample", 1: "Blank", 2:"QC", 3: "Standard Clear (None)", 4: "Standard Update (None)", 5: "Standard Bracket (Open)", 6: "Standard Brcket Start (multiple brackets)", 7: "Standard Bracket End (multiple brackets"}

#%%Get my data 
def GetmyData(rawfile, existing_samples=[]):
    obj0 = Dispatch("MSFileReader.XRawFile");
    obj0.open(str(rawfile))
    obj0.SetCurrentController(Detector_used["MS"],1) #Detector device, the number of detector used (1st, 2nd etc)
    
    creation_date = obj0.GetCreationDate()
    creation_date = dt(creation_date.year,creation_date.month,creation_date.day,creation_date.hour,creation_date.minute,creation_date.second)
    
    if existing_samples is not None and (Path(rawfile).name, creation_date) in existing_samples:
        print(f"The file {Path(rawfile).name} has already been added to the sql database")
        return None, None
       
    functions, data = ReadAllMassList(obj0)
        
    return functions, data

def ReadAllMassList(obj0):
    lst_func =  []
    lst_data = []
    
    numSpec = obj0.GetNumSpectra()
    
    for i in range(numSpec):
        functions, data = GetMassList(obj0,i+1)
        lst_func.append(functions)
        lst_data.append(data)
        
    return clean_data(
        pd.DataFrame(lst_func),
        pd.concat(lst_data, sort=False, ignore_index=True)
        )

#%%Choose information you want by MSFilereader etc.
def GetMassList(obj0, ScanNum, cutoff=1):
    resp = obj0.GetMassListFromScanNum(ScanNum, #Scan number
                                       '', #Scanfilter
                                       0, #Intensity cutoff type
                                       0, #Intensity cutoff value
                                       0, #Number of peaks
                                       1, #bCentroid, 0 for profile MS data and 1 for centroid MS data
                                       0.01, #CentroidPeakWidth
                                       EmptyVariant, 
                                       EmptyVariant, 
                                       )
    ml, il = resp[2]       
    rt = obj0.RTFromScanNum(ScanNum)
    order = obj0.GetMSOrderForScanNum(ScanNum)
    fname = obj0.GetFilterForScanNum(ScanNum)
    DetType = obj0.GetDetectorTypeForScanNum(ScanNum)
    CE = obj0.GetCollisionEnergyForScanNum(ScanNum,order)
    MassAnalyzer = obj0.GetMassAnalyzerTypeForScanNum(ScanNum)
    SampleType = obj0.GetSeqRowSampleType(ScanNum)
    FilePath = os.path.dirname(str(rawfile))
    Filename = Path(str(rawfile)).stem
    creation_date = obj0.GetCreationDate()
    creation_date = dt(creation_date.year,creation_date.month,creation_date.day,creation_date.hour,creation_date.minute,creation_date.second)

    functions = dict(FilePath = FilePath,
                     Filename = Filename,
                     creation_date = creation_date,
                     SampleType = Sample_types.get(SampleType, f"Unknown ({SampleType = })"),
                     scan=ScanNum, 
                     rt=rt, 
                     ms_order=order, 
                     MSfilter=fname, 
                     MSAnalyzer = MS_types.get(MassAnalyzer, f"Unknown ({MassAnalyzer = })"),
                     Detector_type = detector_types.get(DetType, f"Unknown ({DetType = })"),
                     Collision_energy = CE,
                     Date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                     )
    
    data = (pd.DataFrame({"Filename" : Filename,
                          "Datafile created at (YYYY-MM-DD HH-MM-SS)" : creation_date, 
                          "mass": ml, 
                          "intensity":il})
            .loc[lambda df: df["intensity"]> cutoff]
            .assign(scan=ScanNum)
            )
    
    return functions, data

#%%Get information on the precoursor ion
def precursorIon(row):
    if row['ms_order'] == 1:
        val = 0
    else:
        val = row['MSfilter']
    return val

#%%Clen data
def clean_data(functions, data):
    functions = functions.copy()
    data = data.copy()
    
    functions['precursor ion'] = functions["MSfilter"].str.extract(r"ms2 ([0-9]+\.[0-9]+)@").astype(float)
    functions['Ionization'] = [x[5:12] for x in functions['MSfilter']]
    functions['Ionization'].replace({'+ p ESI': 'ESI+', '+ c ESI': 'ESI+', '- p ESI': 'ESI-', '- c ESI': 'ESI-'}, inplace=True)
    functions['MS Range'] = functions['MSfilter'].str.extract('.*\[(.*)\].*')
    functions['ID'] = functions['scan'].astype(str) + "_" + functions['Filename'] + "_" + functions['creation_date'].astype(str)
    
    functions.rename(columns={'scan': 'Scan number', 
                              'rt': 'Retention time',
                              'ms_order': 'MS\u207F',
                              'Collision_energy': 'Collision energy (eV)',
                              'Detector_type': 'Detector type',
                              'MSAnalyzer': 'MS Analyzer',
                              'precursor ion': 'Precursor ion (m/z)', 
                              'Date':'Imported to sql at (YYYY-MM-DD HH-MM-SS)',
                              'SampleType': 'Sample type',
                              'Ionization': 'Ionisation mode',
                              'MS Range': 'MS Range m/z',
                              'creation_date': 'Datafile created at (YYYY-MM-DD HH-MM-SS)',
                              'Unique name': 'ID',
                              'Filename': 'File',
                              'FilePath': 'File path'
                              }, inplace=True)
    del functions['MSfilter']
    
    data.insert(0, "ID", data['scan'].astype(str) + "_" + data['Filename'] + "_" + data['Datafile created at (YYYY-MM-DD HH-MM-SS)'].astype(str))
    del data['Filename']
    del data['Datafile created at (YYYY-MM-DD HH-MM-SS)']
        

    data.rename(columns={'scan': 'Scan number', 
                         'mass': 'Mass',
                         'intensity': 'Intensity'
                         }, inplace=True)

    return functions, data

#%%SQL and choose datafolder definitions 
def writesql(functions, data, db_file=F"{working_directory}/orbitrap.db"):       
    with sqlite3.connect(db_file) as con:
        functions.to_sql("functions", con, if_exists="append", index=False)
        data.to_sql("masslist", con, if_exists="append", index=False)

def set_filename(df):
    df["filename"] = df["File"].apply(lambda f: Path(f).name)
    
def choose_folder(parent):
    import tkinter as tk
    import tkinter.filedialog
    
    root = tk.Tk()
    root.withdraw()
    raw_folder = tkinter.filedialog.askdirectory(parent=root, initialdir=parent, title="Choose folder with raw file(s)")
    return list(Path(raw_folder).glob("*.raw"))

#%% Export data from all raw files in the chosen folder to SQL
if __name__=="__main__":
    db_file=f"{working_directory}/orbitrap.db"
    
    raw_files = choose_folder(working_directory)      
    
    with sqlite3.connect(db_file) as con:
        
        if con.execute("select name from sqlite_master where name='functions'").fetchall():
            existing_samples = pd.read_sql("select distinct file, [Datafile created at (YYYY-MM-DD HH-MM-SS)] from functions", con)
            existing_samples = existing_samples.apply(pd.to_datetime, errors="ignore")
            set_filename(existing_samples)
            
            existing_samples_tuple = existing_samples[["filename", "Datafile created at (YYYY-MM-DD HH-MM-SS)"]].values
            
        
        else:
            existing_samples = None
            existing_samples_tuple = None


    for rawfile in tqdm(raw_files):
        functions, data = GetmyData(rawfile, existing_samples=existing_samples_tuple)
        if functions is None:
            continue
                        
        writesql(functions, data, db_file=db_file)