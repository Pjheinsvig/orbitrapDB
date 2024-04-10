# orbitrapDB

This repository comprises Python code designed to access information from samples aquried using the Thermo Fisher ID-X instrument. To run the code, please install the Thermo Fisher direct-link library "msFileReader" before use. 
The first script (RAWfiles_to_sql_database) reads centroid MS data and selected metadata from Thermo Fisher .raw data files, and structure it in an SQL database consiting of two tables. The second script (EIC plot specific sample) includes illustration of EICs from both the orbitrap and the ion trap.
If you need a file to test the code, the test.raw file ca be used. 
