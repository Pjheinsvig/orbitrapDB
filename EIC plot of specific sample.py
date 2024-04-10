#Part 2A: EIC of specific sample
#%%Import 
import sqlite3 as lite
import matplotlib.pyplot as plt
import pandas as pd
#%%Write name of the sample you want to make a EIC of
SampleofInterest = "MMA_MMA_RPLCPOS_1000_DDA" #Write here the sample name of interest. You can find a list in the File column in the orbitrap database created by script #1
mass = 145
mass_tol = 0.2

#%%Connect to the orbitrap database
working_directory = "C:/Users/XXXX" # Path from where your SQL database is located. Remember to change this
con = lite.connect('orbitrap.db')

#%%Specify the dataframe(s) you want to use from the database table(s) 
info = pd.read_sql_query (f'''
                                SELECT "Scan number","MS\u207F","Precursor ion (m/z)","Retention time", "MS Analyzer", "MS Range m/z"
                               FROM functions
                               WHERE ID like '%{SampleofInterest}%'
                               ''', con)

data = pd.read_sql_query (f'''
                                SELECT
                               *
                               FROM masslist
                               WHERE ID like '%{SampleofInterest}%'
                               AND Mass > {mass - mass_tol}
                               AND Mass < {mass + mass_tol}
                               ''', con)

#Remember to close the database after import of dataframes
con.close()

#%%Define data
FullData = pd.merge(data, info, on="Scan number")
SelectedDetector = "FTMS" #FTMS for orbitrap and ITMS for the iontrap
SelectedDetectorData = FullData[FullData['MS Analyzer'].str.contains(SelectedDetector)]

#%%Plot EIC
plt.plot(SelectedDetectorData["Retention time"], SelectedDetectorData["Intensity"])
plt.xlabel("Retention time [min]")
plt.ylabel("Absolute intensity")
plt.ylim(0, None)
plt.title(f"EIC of {mass} \u00B1 {mass_tol} m/z from the {SelectedDetector} detector", size=15)
plt.show()