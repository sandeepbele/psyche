from openai import OpenAI
import base64
from pprint import pprint
import os 

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Path to your image
#image_path = "/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets/3d7d3dee-7398-41ec-abdd-e33ece52fe44.png"
image_path = "/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/extracted_logos/debug_header_image.png"
# Getting the base64 string
base64_image = encode_image(image_path)

os.environ['OPENAI_LOG'] = 'debug'

client = OpenAI()

#prompt = """Image is a screenshot of a webpage. 
#Please analyze the image and extract the following information: Brand, Brand URL, Business Category, Webpage Summary, Call to Action, Contact Information, Language, Error. 
#If there is any error in the image then provide the error message. 
#Return the answer as a json object."""

prompt = """Image is a annotated screenshot of a webpage. Describe it in detail. 
Identify primary brand/product/logos. Potential brand/logo candidates are marked by green rectangle.
OCR text for each candidate is news and Copitot. OCR may have spelling errors.Look at all the evidence and provide response in form of a json object with following fields:
{brand:string, brand_url:string, business_category:string, webpage_summary:string, cta:string, contact_info:object, language:string, error:string}"""

response = client.chat.completions.create(
  model="gpt-4-vision-preview",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": f"{prompt}"},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/png;base64,{base64_image}",
            "detail":"low"
          },
        },
      ],
    },
  ],
  max_tokens=300,
)

pprint(response.choices[0])
pprint(response.usage)
