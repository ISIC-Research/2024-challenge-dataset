# -*- coding: utf-8 -*-
"""
Created on Tue Nov 14 10:05:09 2023

@author: kurtansn
"""

# specify your parameters for diagnostic labels
folder_labels = r''
file_labels = 'lesion.csv'
patient_col_idx = 0
lesion_col_idx = 1
bxday_col_idx = 2

# specify your parameters for exported tiles
folder_tiles = r'C:\Users\*'
file_tiles = 'patients.csv'

# specify an output directory
out_dir = r'C:\Users\*\ISIC 2024 outdir'

###############################################################################
###############################################################################


# imports
import os
import pandas as pd
from tqdm import tqdm
import glob
from datetime import datetime, timedelta
import shutil


# make outdir
if not os.path.exists(out_dir):
    os.mkdir(out_dir)
if not os.path.exists(r'{}\tags'.format(out_dir)):
    os.mkdir(r'{}\tags'.format(out_dir))

# reads csv - dx labels
df_label = pd.read_csv(r'{}\{}'.format(folder_labels, file_labels))
# remove rows where no patient id
df_label = df_label[df_label.iloc[:, patient_col_idx].isna() == False].reset_index(drop = True)    # 1/16/2024
df_label.iloc[:,patient_col_idx] = ["{:08d}".format(p) for p in df_label.iloc[:,patient_col_idx]]
df_label['proc_date_date'] = [datetime.strptime(i, '%m/%d/%Y').date() for i in df_label.iloc[:,bxday_col_idx]]
df_label['patient_lesion'] = df_label.iloc[:, patient_col_idx] + "_" + df_label.iloc[:, lesion_col_idx].fillna(0).astype(int).astype(str)

# read csv - tile\patient
df_tile_pat = pd.read_csv(r'{}\{}'.format(folder_tiles, file_tiles))
df_tile_pat['Patient ID'] = [str(p).replace("=", "").replace('"', "") for p in df_tile_pat['Patient ID']]
df_tile_pat['MRN'] = [str(p).replace("=", "").replace('"', "") for p in df_tile_pat['MRN']]
df_tile_pat['Capture ID'] = [str(p).replace('"', "").replace('=', "") for p in df_tile_pat['Capture ID']]
df_tile_pat = df_tile_pat[df_tile_pat['Capture ID'] != 'nan'].reset_index(drop = True)
df_tile_pat['capture_date_8chr'] = [i[0:8] for i in df_tile_pat['Capture ID']]
df_tile_pat['capture_date_date'] = None
for ir, row in df_tile_pat.iterrows():
    try:
        df_tile_pat['capture_date_date'][ir] = datetime.strptime(row['capture_date_8chr'], "%Y%m%d").date()
    except ValueError:
        df_tile_pat.drop([ir])   
df_tile_pat = df_tile_pat.reset_index(drop = True)


# initiate metadata storage
metadata = pd.DataFrame()


#  Part 1: loop over lesions with diagnostic labels
print('Part 1... Looping over strong-labelled tiles')
# list of completed tagged lesions
completed_tags = []
for t in tqdm(range(len(df_label))):
    
    # check if lesion is already completed
    tag = '{}_{}'.format(df_label.iloc[t,patient_col_idx], df_label.iloc[t,lesion_col_idx])
    if tag in completed_tags:
        continue 
    completed_tags.append(tag)
    
    # filter df_tile_pat
    df_tile_pat_t = df_tile_pat[df_tile_pat['MRN'] == str(df_label.iloc[t,patient_col_idx])]
          
    # Within 3 months of biopsy
    df_tile_pat_t = df_tile_pat_t[df_tile_pat_t['capture_date_date'] <= df_label['proc_date_date'][t]]
    df_tile_pat_t = df_tile_pat_t[df_tile_pat_t['capture_date_date'] >= (df_label['proc_date_date'][t] + timedelta(days = -91.3125))]
    
    # Check if any 3D images are available
    if len(df_tile_pat_t) == 0:
        continue
        
    # iterate over 3D images
    for tt, row_3d in df_tile_pat_t.iterrows():
        
        # folder
        dir_img3d = r'{}\{}-{}\{}'.format(folder_tiles, row_3d['Patient ID'], row_3d['MRN'], row_3d['Capture ID'])

        # list of tagged tiles
        tiles = glob.glob(r'{}\tiles_tagged*\{}_*'.format(dir_img3d, df_label.iloc[t,lesion_col_idx]))
        
        # if empty, next
        if tiles == []:
            continue
        else:
            # check for csv
            if glob.glob(r'{}\*.csv'.format(dir_img3d)) == []:
                continue

            # read csv
            df_tile_img = pd.read_csv(glob.glob(r'{}\*.csv'.format(dir_img3d))[0])
            # identify the lesion
            df_tile_img = df_tile_img[df_tile_img['tag_num'].astype(float) == float(df_label.iloc[t, lesion_col_idx])].reset_index(drop = True)
            
            # if empty, next
            if len(df_tile_img) < 1:
                continue
            else:
                if not os.path.exists(r'{}\{}'.format(out_dir, row_3d['Patient ID'])):
                    # make patient subfolder output directory
                    os.mkdir(r'{}\{}'.format(out_dir, row_3d['Patient ID']))
    
                for ttt, row_tile in df_tile_img.iterrows():
                    # copy tile
                    fn = r'tags\{}_{}-{}.jpg'.format(int(row_tile['tag_num']), row_3d['Patient ID'], row_tile['uuid'])
                    shutil.copy2(src = r'{}\{}'.format(dir_img3d, row_tile['isic_tile_file']), dst = r'{}\{}'.format(out_dir, fn))
                    # append metadata
                    metadata = pd.concat([metadata, pd.concat([pd.Series({'filename':fn}), row_3d, row_tile]).to_frame().T])


#  Part 2: loop over all patients
print('Part 2... Looping over weak-labelled tiles')
# list of completed patients
completed_pats = []
for t in tqdm(range(len(df_label))):
    
    # check if patient is already completed
    patient = df_label.iloc[t,patient_col_idx]
    if patient in completed_pats:
        continue
    completed_pats.append(patient)
    
    # filter df_tile_pat
    df_tile_pat_t = df_tile_pat[df_tile_pat['MRN'] == str(df_label.iloc[t,patient_col_idx])].sort_values(by = 'Capture ID', ascending = False).reset_index(drop = True)
    
    # check if any 3D images are availabile
    if len(df_tile_pat_t) == 0:
        continue
        
    # starting with newest image, check for tags.
    # select the index 3d image for this patient's non-tagged tiles
    index = None
    for tt, row_3d in df_tile_pat_t.iterrows():
        
        # if no tagged tiles, check the next iteration
        if glob.glob(r'{}\{}-{}\{}\tiles_tagged*'.format(folder_tiles, row_3d['Patient ID'], row_3d['MRN'], row_3d['Capture ID'])) == []:
            continue
        else:
            index = tt
            break
    # otherwise, take the newest 3d image
    if index == None:
        index = 0
    
    # folder of 3D image
    dir_img3d = r'{}\{}-{}\{}'.format(folder_tiles, df_tile_pat_t['Patient ID'][index], df_tile_pat_t['MRN'][index], df_tile_pat_t['Capture ID'][index])
    
    # read csv
    try:
        df_tile_img = pd.read_csv(glob.glob(r'{}\*csv'.format(dir_img3d))[0])
    except IndexError:
        continue
           
    # identify rows in the csv
    # filter 1: remove strong labelled lesions
    df_tile_img = df_tile_img.loc[['{}_{}'.format(df_label.iloc[t, patient_col_idx], int(i)) not in completed_tags for i in df_tile_img['tag_num'].fillna(0)]]
    
    # filter 2: lesion status 1 or Null (i.e. not labeled 'Biopsied', 'Excised')
    df_tile_img = df_tile_img.loc[[i not in ['Biopsy', 'Excised'] for i in df_tile_img['tag_status_name']]]

    # filter 3: uuid not null (i.e. tile is not unmatched)
    df_tile_img = df_tile_img.loc[[i != '' for i in df_tile_img['uuid'].fillna('')]]
    
    if len(df_tile_img) < 1:
        continue
    
    else:
        # if not already in existence, make patient subfolder in output directory
        out_dir_p = r'{}\{}'.format(out_dir, df_tile_pat_t['Patient ID'][index])
        if not os.path.exists(out_dir_p):
            os.mkdir(out_dir_p)
            
        # iterate over tiles
        for ttt, row_tile in df_tile_img.iterrows():
            # copy tile
            fn = r'{}\{}-{}.jpg'.format(df_tile_pat_t['Patient ID'][index], df_tile_pat_t['Patient ID'][index], row_tile['uuid'])
            shutil.copy2(src = r'{}\{}'.format(dir_img3d, row_tile['isic_tile_file']), dst = r'{}\{}'.format(out_dir, fn))
            # append metadata
            metadata = pd.concat([metadata,pd.concat([pd.Series({'filename':fn}), df_tile_pat_t.iloc[index,:], row_tile]).to_frame().T])
   
      
    
# Part 3: write metadata file
# join with dx labels table
metadata['patient_lesion'] = metadata['MRN'] + '_' + metadata['tag_num'].fillna(0).astype(int).astype(str)
# write metadata file
pd.merge(metadata, df_label.drop(columns = ['MRN'], errors = 'ignore'), how = 'left', on='patient_lesion').to_csv(r'{}\metadata.csv'.format(out_dir), index = False)
print('Complete!')

    
    