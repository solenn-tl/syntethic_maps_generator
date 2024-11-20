import glob
import os

BASE = "E:/codes/cadastre_synth_maps"
OUTPUT = BASE + "/outputs"

imgs = sorted(glob.glob(OUTPUT + "/*.csv"))

for img in imgs:

    image_path = img
    image_path = image_path.replace("prov_region", "tmp_region")
    
    os.rename(img,image_path)
