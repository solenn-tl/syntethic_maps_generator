#I want to iterate over the images and check tha the numerical suite is continuous
import os
import glob

images = glob.glob("E:/codes/cadastre_synth_maps/images/*.jpg")
images = sorted(images, key=lambda x: int(x.split("_")[-1].replace(".jpg", "")))

last_image_number = 0
for image in images:
    image_name = image.split("/")[-1]
    image_number = int(image_name.split("_")[-1].replace(".jpg", ""))
    if image_number != last_image_number + 1:
        print(f"Error in {image_name}")
    last_image_number = image_number
