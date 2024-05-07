# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 10:09:22 2024

@author: kurtansn
"""

# imports
import os
import pandas as pd

# SPECIFY YOUR PARAMETERS
folder = r'' 			# location of the metadata file
file = '' 				# metadata filename
patient_column_idx = 0 	# column index for MRN/patient_id within the metadata file

# changes directory
os.chdir(folder)

# reads csv
df = pd.read_csv(file)

# remove rows where no patient id
df = df[df.iloc[:, patient_column_idx].isna() == False].reset_index(drop = True)

# unique patient list with leading zeros
s_patients = set(["{:08d}".format(int(p)) for p in df.iloc[:,patient_column_idx]])

# open file and iterate
f = open('VectraDBTool_input.txt', 'w')
for p in sorted(s_patients):
    f.write('{}\n'.format(p))
f.close()
    