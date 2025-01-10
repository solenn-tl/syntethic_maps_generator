import os
import pandas as pd
import plotly
import json

BASE = "E:/codes/cadastre_synth_maps"
GT = BASE + "/gt_v2.json"

#Open json
with open(GT, "r") as f:
    data = json.load(f)

#Number of images
image_paths = []
for img in data:
    image_paths.append(img[0]["image_path"])
image_paths = list(set(image_paths))
print(f"Number of images: {len(image_paths)}")

#Number of groups
groups = []
for img in data:
    groups.append(img[0]["groups"])
groups = [item for sublist in groups for item in sublist]
print(f"Number of groups: {len(groups)}")

#Number of words
words = []
for group in groups:
    for word in group:
        words.append(word["text"])
print(f"Number of words: {len(words)}")

#Count number of words that have truncated=True
truncated = []
for group in groups:
    for word in group:
        truncated.append(word["truncated"])
print(f"Number of words that have truncated=True: {len([word for group in groups for word in group if word['truncated'] == 'True'])}")

#Number of words of each type
types = []
for group in groups:
    for word in group:
        types.append(word["type"])
#Count number of each type
types = list(set(types))
for type_ in types:
    print(f"Number of words of type {type_}: {len([word for group in groups for word in group if word['type'] == type_])}")

#Number of group of each type (take the type of the first word)
types = []
for group in groups:
    types.append(group[0]["type"])
types = list(set(types))
for type_ in types:
    print(f"Number of groups of type {type_}: {len([group for group in groups if group[0]['type'] == type_])}")
    
#Create a list with the number of words in each image
num_words = []
for img in data:
    num_words.append(len([word for group in img[0]["groups"] for word in group]))
print(f"Min number of words in an image: {min(num_words)}")
print(f"Max number of words in an image: {max(num_words)}")
print(f"Average number of words in an image: {sum(num_words)/len(num_words)}")

#Median number of words in an image
num_words.sort()
if len(num_words) % 2 == 0:
    median = (num_words[len(num_words)//2] + num_words[len(num_words)//2 - 1]) / 2
else:
    median = num_words[len(num_words)//2]
print(f"Median number of words in an image: {median}")

#Compute quantiles
quantiles = [0.25, 0.5, 0.75]
quantiles_values = []
for q in quantiles:
    quantiles_values.append(num_words[int(len(num_words)*q)])
print(f"Quantiles: {quantiles_values}")

#Compute average of words of each type by image
types = []
for img in data:
    for group in img[0]["groups"]:
        types.append(group[0]["type"])
types = list(set(types))
for type_ in types:
    num_words = []
    for img in data:
        num_words.append(len([word for group in img[0]["groups"] for word in group if word["type"] == type_]))
    print(f"Average number of words of type {type_} in an image: {sum(num_words)/len(num_words)}")

#Compute quantiles of words of each type by image
types = []
for img in data:
    for group in img[0]["groups"]:
        types.append(group[0]["type"])
types = list(set(types))
for type_ in types:
    num_words = []
    for img in data:
        num_words.append(len([word for group in img[0]["groups"] for word in group if word["type"] == type_]))
    num_words.sort()
    quantiles_values = []
    for q in quantiles:
        quantiles_values.append(num_words[int(len(num_words)*q)])
    print(f"Quantiles of words of type {type_}: {quantiles_values}")

