# django management command 

from typing import Dict, List, Optional, Union
from django.core.management.base import BaseCommand
import subprocess
import uuid
import os

from pydantic import BaseModel

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

from llama_index.multi_modal_llms import OllamaMultiModal

def take_screenshot(url, screenshot_output_dir, seccomp_path):
    screenshot_name = f"{uuid.uuid4()}.png"
    #host_dir = "/path/to/your/host/directory"  # Ensure this directory exists and is writable
    #seccomp_path = "/path/to/your/seccomp_profile.json"  # Adjust the path to your seccomp profile

    # Update the Docker command with the new options
    docker_command = [
        "docker", "run", "-it", "--rm", 
        "--ipc=host", 
        "--user", "pwuser", 
        "--security-opt", f"seccomp={seccomp_path}",
        "-v", f"{screenshot_output_dir}:/screenshots",  # Mount volume for screenshots
        "mcr.microsoft.com/playwright/python:v1.41.0-jammy",  # Specify the Docker image
        "/bin/bash", "-c",  # Use bash to execute the Python script
        f"""
        pip install --upgrade pip
        pip install playwright
        export PATH=$PATH:/home/pwuser/.local/bin
        playwright install
        python -c '
from playwright.sync_api import sync_playwright
with sync_playwright() as playwright:
    firefox = playwright.firefox
    browser = firefox.launch()
    page = browser.new_page()
    page.goto("{url}")
    page.screenshot(path="/screenshots/{screenshot_name}",full_page=True)
    browser.close()     
        '"""
    ]
    print("Running Docker command:", " ".join(docker_command))
    # Execute the Docker command
    result = subprocess.run(docker_command, capture_output=True, text=True)
    
    # Check the result of the Docker command
    if result.returncode == 0:
        print("Screenshot taken successfully.")
        return {"screenshot_path": os.path.join(screenshot_output_dir, screenshot_name), "error": None}
    else:
        print("Failed to take screenshot.", result.stdout)
        print("Error:", result.stderr)
        return {"screenshot_path": None, "error": f"{result.stderr}{result.stdout}"}

def ollama_summarize_image(image_path):

    mm_model = OllamaMultiModal(model="llava")

    from pydantic import BaseModel
    from llama_index.schema import ImageDocument

    """
    class WebPageDesc(BaseModel):
        brand: Optional[str]
        domain: Optional[str]
        business_category: Optional[str]
        webpage_intent: Optional[str]
        webpage_summary: Optional[str]
        cta: Optional[str]  # Call to Action
        contact_info: Optional[Union[str, Dict]]
        language: Optional[str]
        error: Optional[str]
        
        # Added fields for scam, fraud, and phishing detection
        dark_ui_patterns: Optional[List[str]]  # List of identified dark UI patterns, popups, alerts, etc.
        deceiving_language: Optional[List[str]]  # List of phrases or patterns indicating deception, urgency, etc.
        spelling_errors: Optional[List[str]]  # List of spelling errors
        too_good_to_be_true_offers: Optional[List[str]]  # List of offers that seem unrealistic
        scam_indicators: Optional[List[str]]  # General indicators of scam
        phishing_indicators: Optional[List[str]]  # Specific indicators of phishing attempts
        misleading_ctas: Optional[List[str]]  # Call to actions that might be misleading or deceptive
    """

    """Please provide a detailed analysis of the attached webpage. Focus on the following elements:

            Branding: Identify and describe the brand featured on the page, including any logos or brand names visible.
            Product Information: Examine the main product advertised, including its name, features, and any technical specifications listed.
            Pricing Strategy: Assess the pricing details provided, including the original and discounted prices, and comment on the discount's significance and typicality in retail.
            Sales Tactics: Evaluate any sales tactics used, such as the promotion of urgency, countdown timers, or limited availability notices, and their impact on consumer behavior.
            Call to Action: Identify and describe the call to action (CTA) used to encourage user interaction, such as a "Buy Now" button or a subscription form.
            Contact Information: Identify and describe any contact information provided, such as a phone number, email address, or physical address typically present in footer.
            Language: Identify and describe the language used on the page, including any multilingual content or language-specific features.
            UI/UX Design: Evaluate the user interface and user experience design, including any dark patterns, misleading elements, or deceptive practices.
            Anomalies: Identify and describe any anomalies, errors, spelling errors, or suspicious elements that could indicate a scam, fraud, or phishing attempt.
    """


    class WebPageDesc(BaseModel):
        """Data model for webpage description."""

        brand: Optional[str]
        domain: Optional[str]
        business_category: Optional[str]
        webpage_intent: Optional[str]
        cta: Optional[str]
        contact_info: Optional[Union[str,Dict]]
        language: Optional[str]
        error: Optional[str]

    from llama_index.program import MultiModalLLMCompletionProgram
    from llama_index.output_parsers import PydanticOutputParser

    image_documents = [
         ImageDocument(image_path=image_path)
    ]

    prompt_template_str = """\
    You are given a screenshot of a webpage.  
    
    {query_str}

    Return the answer as a Pydantic object. The Pydantic schema is given below:

    """
    mm_program = MultiModalLLMCompletionProgram.from_defaults(
        output_parser=PydanticOutputParser(WebPageDesc),
        image_documents=image_documents,
        prompt_template_str=prompt_template_str,
        multi_modal_llm=mm_model,
        verbose=True,
    )

    response = mm_program(query_str="Extract brand name/logo, domain, call to action(CTA), intent, contact info from footer and language from the image.\
                          If there is any error in the image then provide the error message.")
    for res in response:
        print(res)


def openai_image_summarize(image_path):

    class WebPageDesc(BaseModel):
        brand: Optional[str]
        brand_url: Optional[str]
        business_category: Optional[str]
        webpage_summary: Optional[str]
        cta: Optional[str]  # Call to Action
        contact_info: Optional[Union[str, Dict]]
        language: Optional[str]
        error: Optional[str]
        
        # Added fields for scam, fraud, and phishing detection
        dark_ui_patterns: Optional[List[str]]  # List of identified dark UI patterns, popups, alerts, etc.
        deceiving_language: Optional[List[str]]  # List of phrases or patterns indicating deception, urgency, etc.
        spelling_errors: Optional[List[str]]  # List of spelling errors
        too_good_to_be_true_offers: Optional[List[str]]  # List of offers that seem unrealistic
        scam_indicators: Optional[List[str]] # anomalies from typical brand practices


    # use llamaindex
    from llama_index.multi_modal_llms import OpenAIMultiModal
    from llama_index import SimpleDirectoryReader

    # put your local directory here
    image_documents = SimpleDirectoryReader("./restaurant_images").load_data()

    openai_mm_llm = OpenAIMultiModal(
        model="gpt-4-vision-preview", api_key=OPENAI_API_KEY, max_new_tokens=1000
    )

    from llama_index.program import MultiModalLLMCompletionProgram
    from llama_index.output_parsers import PydanticOutputParser

    prompt_template_str = """\
        can you summarize what is in the image\
        and return the answer with json format \
    """
    openai_program = MultiModalLLMCompletionProgram.from_defaults(
        output_parser=PydanticOutputParser(WebPageDesc),
        image_documents=image_documents,
        prompt_template_str=prompt_template_str,
        multi_modal_llm=openai_mm_llm,
        verbose=True,
    )


def tessaract_image_summarize_tostr(image_path):
    from PIL import Image
    import pytesseract
    from io import BytesIO
    import re
    import json
    from pydantic import BaseModel, validator
    from typing import Optional, Union, List, Dict

    # Load the image from file
    image = Image.open(image_path)
    #os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/Cellar/tesseract/5.3.3/share/tessdata/'
    #tessdata_dir_config = r'--tessdata-dir "/opt/homebrew/Cellar/tesseract/5.3.3/share/tessdata/"'
    # Use pytesseract to extract text from the image
    extracted_text = pytesseract.image_to_string(image,output_type=pytesseract.Output.DICT)
    return extracted_text

def tessaract_image_summarize(image_path):
    from PIL import Image
    import pytesseract
    from io import BytesIO
    import re
    import json
    from pydantic import BaseModel, validator
    from typing import Optional, Union, List, Dict

    # Load the image from file
    image = Image.open(image_path)
    os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/Cellar/tesseract/5.3.3/share/tessdata/'
    tessdata_dir_config = r'--tessdata-dir "/opt/homebrew/Cellar/tesseract/5.3.3/share/tessdata/"'
    # Use pytesseract to extract text from the image
    extracted_text = pytesseract.image_to_string(image,config=tessdata_dir_config,output_type=pytesseract.Output.DICT)
    #extracted_text = pytesseract.image_to_alto_xml(image,config=tessdata_dir_config)

    #print(extracted_text)

    import xml.etree.ElementTree as ET
    import gzip

    def compress_alto_xml(input_xml_path, output_xml_path):
        tree = ET.parse(input_xml_path)
        root = tree.getroot()

        # Iterate through the XML tree and remove unnecessary attributes
        for page in root.findall('.//Page'):
            for block in page.findall('.//TextBlock'):
                for line in block.findall('.//TextLine'):
                    for string in line.findall('.//String'):
                        # Keep only the CONTENT attribute which contains the text
                        for attr in list(string.attrib):
                            if attr != 'CONTENT':
                                del string.attrib[attr]

                        # If you want to remove the TextLine elements themselves
                        # line.clear()

        # Write out the modified XML
        tree.write(output_xml_path, encoding='utf-8', xml_declaration=True)

    
    import xml.etree.ElementTree as ET

    def split_alto_xml(alto_xml_string):

        header_blocks = footer_blocks = body_blocks = []

        # Parse the XML string
        root = ET.fromstring(alto_xml_string)

        # Assuming the structure has a root <alto> tag
        pages = root.findall('.//Page')
        print(pages)

        for page in pages:

            page_width = int(page.attrib['WIDTH'])
            page_height = int(page.attrib['HEIGHT'])

            # Define the header and footer cutoffs as percentages of the page height
            header_percentage = 0.10  # 10% of the page height
            footer_percentage = 0.10  # 10% of the page height

            header_cutoff = page_height * header_percentage
            footer_cutoff = page_height * (1 - footer_percentage)

            text_blocks = page.findall('.//TextBlock')

            header_blocks = [tb for tb in text_blocks if int(tb.attrib['VPOS']) < header_cutoff]
            footer_blocks = [tb for tb in text_blocks if int(tb.attrib['VPOS']) > footer_cutoff]
            body_blocks = [tb for tb in text_blocks if tb not in header_blocks + footer_blocks]

            # Process the header, body, and footer blocks as needed
            # ...

        # Return or process the separated segments as required
        return header_blocks, body_blocks, footer_blocks


    #(header,footer,body) = split_alto_xml(extracted_text)

    #print(extracted_text)
    return extracted_text


def ollama_ask_llm(text):

    prompt2 = f"""\
        You are given ocr output of a webpage.\
        Extract brand name/logo, domain, call to action(CTA), intent, contact info from footer and language from the image.\
        If there is any error in the image then provide the error message.\
        and return the answer with json format. \
        OCR text: {text}
    """
    prompt = f"""##You are given ocr output of a webpage.Please provide a detailed analysis of the text. Focus on the following elements:

            Branding: Identify and describe the brand featured on the page, including any logos or brand names visible.
            Product Information: Examine the main product advertised, including its name, features, and any technical specifications listed.
            Pricing Strategy: Assess the pricing details provided, including the original and discounted prices, and comment on the discount's significance and typicality in retail.
            Sales Tactics: Evaluate any sales tactics used, such as the promotion of urgency, countdown timers, or limited availability notices, and their impact on consumer behavior.
            Call to Action: Identify and describe the call to action (CTA) used to encourage user interaction, such as a "Buy Now" button or a subscription form.
            Contact Information: Identify and describe any contact information provided, such as a phone number, email address, or physical address typically present in footer.
            Language: Identify and describe the language used on the page, including any multilingual content or language-specific features.
            Anomalies: Identify and describe any anomalies, errors, spelling errors, or suspicious elements that could indicate a scam, fraud, or phishing attempt.

            ## Return response *ONLY as json* with fields:
            ** brand:string, brand_url:string, business_category:string, webpage_summary:string, cta:string, contact_info:dict, 
            language:string, error:string, deceiving_language:list[string], spelling_errors:list[string], 
            offers:list[string], urgency:list[string] **
              
            ## OCR output of webpage: {text}
    """

    from llama_index.llms import Ollama
    import json

    llm = Ollama(model="mistral", request_timeout=300.0)
    resp = llm.complete(prompt)
    print(resp)
    return resp


def is_url_suspicious(suspect_url):

    import numpy as np
    import onnxruntime
    from huggingface_hub import hf_hub_download

    REPO_ID = "pirocheto/phishing-url-detection"
    FILENAME = "model.onnx"
    model_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)

    # Initializing the ONNX Runtime session with the pre-trained model
    sess = onnxruntime.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )

    urls = [
        suspect_url,
        "https://clubedemilhagem.com/home.php",
        "http://www.medicalnewstoday.com/articles/188939.php",
    ]
    inputs = np.array(urls, dtype="str")

    # Using the ONNX model to make predictions on the input data
    results = sess.run(None, {"inputs": inputs})[1]

    for url, proba in zip(urls, results):
        print(f"URL: {url}")
        print(f"Likelihood of being a phishing site: {proba[1] * 100:.2f} %")
        print("----")

from urllib.parse import urlparse
import re

import tldextract

def match_urls_ignore_subdomains(url1, url2):
    
    if url1 is None or url1 == "" or url2 is None or url2 == "":
        return False
   
    # Extract the domain and suffix from each URL
    extracted1 = tldextract.extract(url1)
    extracted2 = tldextract.extract(url2)
    
    # Reconstruct the main domain without subdomains
    domain1 = "{}.{}".format(extracted1.domain, extracted1.suffix)
    domain2 = "{}.{}".format(extracted2.domain, extracted2.suffix)
    
    # Optionally, compare paths as well
    #path1 = urlparse(url1).path
    #path2 = urlparse(url2).path
    
    # Normalize paths by lowercasing (optional, based on requirement)
    #path1, path2 = path1.lower(), path2.lower()
    
    # Compare main domain and path
    return domain1 == domain2 #and path1 == path2


def get_brand_url_from_file(brand, file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if brand.lower() in line:
                return line.strip()  # Assuming each line is a URL
    return None

def is_phishing_url(url,brand_url,brand) -> bool:
    
    from django.conf import settings
    cloudflare_radar_domains_file = os.path.join(settings.BASE_DIR, "cloudflare-radar-domains-top-100000-20240129-20240205.csv")
    if brand_url is None or brand_url == "":
        brand_url = get_brand_url_from_file(brand, cloudflare_radar_domains_file)
    
    return not match_urls_ignore_subdomains(url, brand_url)