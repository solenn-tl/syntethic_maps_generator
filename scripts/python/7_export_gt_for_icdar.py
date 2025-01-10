import glob
import os
import json
import pandas as pd

BASE = "E:/codes/cadastre_synth_maps"
OUTPUT = BASE + "/outputs"

csvs = sorted(glob.glob(OUTPUT + "/region_*.csv"))
csvs = sorted(csvs, key=lambda x: int(x.split("_")[-1].replace(".csv", "")))

#Create an empty json
json_ = []

for csv in csvs:

    image_path = csv.replace(".csv", ".jpg")
    image_final_path = image_path.replace(OUTPUT, "")
    image_final_path = image_final_path.replace('\\', "")
    image_final_path = image_final_path.replace('.jpg', "")

    img_annotations = []
    img_annotations.append({
        "image_path": image_final_path,
        "groups": ""
        #style
    })
    #Open the csv
    df = pd.read_csv(csv)
    #Get the ist of distinct values in feature_id
    feature_ids = df["feature_id"].unique()
    #Iterate over group of rows that have the same feature id
    groups = []

    counter = 0
    for feature_id in feature_ids:
        group = df[df["feature_id"] == feature_id]
        type_ = group.iloc[0]["layer"]
        group_lst = []
        for i in range(len(group)):
            #Create a geojson feature
            feature = {
                "vertices": group["geometry"].iloc[i],
                "text": str(group["label"].iloc[i]),
                "illegible":str(False),
                "truncated": str(group["truncated"].iloc[i]),
                "type": type_
                }
            group_lst.append(feature)
        #Append the feature to the json
        groups.append(group_lst)
    #Append the groups to the json
    img_annotations[0]["groups"] = groups
    json_.append(img_annotations)

#Save the json
with open(BASE + "/gt_v2.json", "w") as f:
    json.dump(json_, f)