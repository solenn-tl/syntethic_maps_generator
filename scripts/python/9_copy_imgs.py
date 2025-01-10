#Copy all '.jpg' files from "outputs" to "images" folder
import glob
import shutil
import os

BASE = "E:/codes/cadastre_synth_maps"
OUTPUT = BASE + "/outputs"

imgs = glob.glob(OUTPUT + "/*.jpg")

for img in imgs:
    shutil.copy(img, img.replace("outputs", "images"))