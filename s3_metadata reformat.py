# -*- coding: utf-8 -*-
"""
Created on Fri Dec  8 10:48:42 2023

@author: kurtansn
"""

## Parameters
# specify directory
tile_dir = r''

########################################

meta_fn = r'metadata.csv'

# imports
import pandas as pd
import numpy as np
import os
import datetime
import hashlib

# load metadata file
meta = pd.read_csv(r'{}/{}'.format(tile_dir, meta_fn))

# remove rows where image does not exist
meta = meta.iloc[[i for i, n in enumerate(meta['filename']) if os.path.isfile(r'{}/{}'.format(tile_dir, n))], :]

# de-identified acquisition_day
meta['acquisition_day'] = [
    (datetime.datetime.strptime(str(vid)[:8], '%Y%m%d') -
     (datetime.datetime(1900, 1, 1) +
      datetime.timedelta(
          days=int(hashlib.md5(str(vmrn).encode('ascii')).hexdigest()[3::8], 16) % 32768
      ))).days for vid, vmrn in zip(meta['Capture ID'], meta['MRN'])
]

# drop columns
drops = [
        "anatom_site_general",
        "MRN",
        "MRN_x", 
        "MRN_y",
        "Capture ID",
        "capture_date_8chr",
        "capture_date_date",
        "isic_tile_file",
        "Unnamed: 46",
        "Unnamed: 56",
        "mrn_lesion",
        "patient_lesion",
        "case_id",
        "pathrpt",
        "mrn",
        "vectra",
        "proc_date",
        "proc_date_date",
        "proc_date_8chr",
        "isic_tile_px",
        "tag_dist_mm",
        "tag_style_id",
        "tag_status_id",
        "biopsy_date",
        "patient"
        ]

meta = meta.drop(columns = drops, errors = 'ignore').rename(columns = {'Patient ID':'patient_id', 'majorAxisMM':'clin_size_long_diam_mm'}).reset_index(drop = True)


# lesion_id
lesion_id = ['' for i in range(len(meta))]
for i, row, in meta.iterrows():
    try:
        lesion_id[i] = '{}_{}'.format(row['patient_id'], int(row['tag_num']))
    except:
        continue
meta.insert(2, 'lesion_id', lesion_id)

# replace NaN with empty strings
meta = meta.replace(np.nan, '')



# mapping directories
tilemap = {'XP': '3D: XP',
           'STD': '3D: white',
           '': ''}

lmap = {'Head & Neck': 'head/neck', 
        'Left Arm': 'upper extremity',
        'Left Leg': 'lower extremity',
        'Right Arm': 'upper extremity',
        'Right Leg': 'lower extremity',
        'Torso Back': 'posterior torso',
        'Torso Front': 'anterior torso',
        'Unknown': ''}

agemap = {'15-20': 17,
          '20-25': 22,
          '25-30': 27,
          '30-35': 32,
          '35-40': 37,
          '40-45': 42,
          '45-50': 47,
          '50-55': 52,
          '55-60': 57,
          '60-65': 62,
          '65-70': 67,
          '70-75': 72,
          '75-80': 77,
          '80-85': 82,
          '85-90': 87,
          '' : ''}

meltypemap = {'lmm': 'lentigo maligna melanoma',
              'ssm': 'superficial spreading melanoma',
              'alm': 'acral lentiginous melanoma'}

# sets
dxotherset = {'cyst'}
meldxset = {'melanoma', 'squamous cell carcinoma', 'basal cell carcinoma', 'melanoma metastasis'}
dxset = set(meta['diagnosis'])
dxset.remove('')

# image_type
meta['image_type'] = 'TBP tile: close-up'

# TBP tile type
meta['tbp_tile_type'] = [tilemap.get(v, v) for v in meta['3D Modality']]

# age
meta['age'] = [agemap.get(v, v) for v in meta['Age']]

# sex
meta['sex'] = meta['Sex'].str.lower()

# anatom_site_general
meta['anatom_site_general'] = [lmap.get(v, v) for v in meta['location_simple']]

# filename
meta['filename'] = [f.split('\\')[-1] for f in meta['filename']]

# benign_malignant
meta['benign_malignant'] = ['malignant' if i in meldxset else 'benign' for i in meta['diagnosis']]

# diagnosis confirm type
meta['diagnosis_confirm_type'] = ['histopathology' if i in dxset else '' for i in meta['diagnosis']]

# mel_class
meta['mel_class'] = meta['mel_class'].str.lower()

# mel_type
meta['mel_type'] = [meltypemap.get(v, v) for v in meta['mel_type']]

# diagnosis_other_txt
meta['diagnosis_other_txt'] = [i if i in dxotherset else '' for i in meta['diagnosis']]

# diagnosis should be 'other'
meta['diagnosis'] = [i if i not in dxotherset else 'other' for i in meta['diagnosis']]

# replace NaN with empty string and write metadata file
meta.drop(columns = ['Sex']).replace(np.nan, '').replace('', '').to_csv('{}\metadata_revised.csv'.format(tile_dir), index = False)
print('Complete!')


# Get a tuple of unique values 
# and their frequency in
# numpy array
unique, frequency = np.unique(meta.mel_class, 
                              return_counts = True) 
# convert both into one numpy array 
# and then transpose it
np.asarray((unique,frequency )).T