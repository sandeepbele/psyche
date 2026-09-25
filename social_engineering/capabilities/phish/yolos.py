from PIL import Image
import requests
import numpy as np
import cv2

url = 'http://images.cocodataset.org/val2017/000000039769.jpg'

#image = Image.open(requests.get(url, stream=True).raw)
#image = Image.open("/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets/3d7d3dee-7398-41ec-abdd-e33ece52fe44.png")
# read image from file
image_path = '/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets/3d7d3dee-7398-41ec-abdd-e33ece52fe44.png'
#image = Image.open(image_path)
#image = np.array(image)
image = cv2.imread(image_path)

from transformers import AutoFeatureExtractor

feature_extractor = AutoFeatureExtractor.from_pretrained("hustvl/yolos-small")

pixel_values = feature_extractor(image, return_tensors="pt").pixel_values
pixel_values.shape

from transformers import YolosForObjectDetection

model = YolosForObjectDetection.from_pretrained("hustvl/yolos-small")

import torch

with torch.no_grad():
  outputs = model(pixel_values, output_attentions=True)


import matplotlib.pyplot as plt

# colors for visualization
COLORS = [[0.000, 0.447, 0.741], [0.850, 0.325, 0.098], [0.929, 0.694, 0.125],
          [0.494, 0.184, 0.556], [0.466, 0.674, 0.188], [0.301, 0.745, 0.933]]

def plot_results(pil_img, prob, boxes):
    plt.figure(figsize=(16,10))
    plt.imshow(pil_img)
    ax = plt.gca()
    colors = COLORS * 100
    for p, (xmin, ymin, xmax, ymax), c in zip(prob, boxes.tolist(), colors):
        ax.add_patch(plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                                   fill=False, color=c, linewidth=3))
        cl = p.argmax()
        text = f'{model.config.id2label[cl.item()]}: {p[cl]:0.2f}'
        ax.text(xmin, ymin, text, fontsize=15,
                bbox=dict(facecolor='yellow', alpha=0.5))
    plt.axis('off')
    plt.show()

# keep only predictions of queries with 0.9+ confidence (excluding no-object class)
probas = outputs.logits.softmax(-1)[0, :, :-1]
keep = probas.max(-1).values > 0.9

# rescale bounding boxes
_, height, width = image.shape
target_sizes = torch.tensor([width, height]).unsqueeze(0)
postprocessed_outputs = feature_extractor.post_process(outputs, target_sizes)
bboxes_scaled = postprocessed_outputs[0]['boxes']

plot_results(image, probas[keep], bboxes_scaled[keep])