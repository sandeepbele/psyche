import requests
from PIL import Image
from transformers import Pix2StructForConditionalGeneration, Pix2StructProcessor


print("Loading model...")
#model = Pix2StructForConditionalGeneration.from_pretrained("google/pix2struct-textcaps-base").to("cuda")
model = Pix2StructForConditionalGeneration.from_pretrained("google/pix2struct-textcaps-base")
print("Loading processor...")
processor = Pix2StructProcessor.from_pretrained("google/pix2struct-textcaps-base")
print("Done!")

image = Image.open("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/coinbase.png").convert("RGB")
print("Image size:", image.size)

#texts = ["webpage is asking user", "webpage says its for","webpage asking user to give away"]
texts = ["purpose of webpage is","webpage talks about product","webpage describes a service"]
# image only
for text in texts:
    print("Text:", text)
    #inputs = processor(images=image, text=text, return_tensors="pt").to("cuda")
    
    inputs = processor(images=image, text=text, return_tensors="pt")
    #print("Input size:", inputs.input_ids.size())
    predictions = model.generate(**inputs)
    #print("Prediction size:", predictions.size())
    print(processor.decode(predictions[0], skip_special_tokens=True))

# 