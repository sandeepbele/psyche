from PIL import Image
import pytesseract
from io import BytesIO
import re
import json
from pydantic import BaseModel, validator
from typing import Optional, Union, List, Dict
import os

"""image_path = "/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets/3d7d3dee-7398-41ec-abdd-e33ece52fe44.png"
# Load the image from file
image = Image.open(image_path)
#os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/Cellar/tesseract/5.3.3/share/tessdata/'
#tessdata_dir_config = r'--tessdata-dir "/opt/homebrew/Cellar/tesseract/5.3.3/share/tessdata/"'
# Use pytesseract to extract text from the image
extracted_text = pytesseract.image_to_string(image,output_type=pytesseract.Output.DICT)

print(extracted_text)

extracted_text = pytesseract.image_to_alto_xml(image)
print(extracted_text)"""


import cv2
import numpy as np
import pytesseract
from pytesseract import Output

# Set the path for Tesseract if necessary
# pytesseract.pytesseract.tesseract_cmd = r'<path_to_tesseract>'

# Load the image
image_path = '/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets/3d7d3dee-7398-41ec-abdd-e33ece52fe44.png'
image = cv2.imread(image_path)

current_dir = os.getcwd()
logo_dir = os.path.join(current_dir, 'extracted_logos')

# Define the header section as a percentage of the page height, say the top 25%
header_section_height = int(image.shape[0] * 0.25)
header_section_width = image.shape[1]

# The header ROI is the slice of the image from the top down to the defined height
header_roi = image[0:header_section_height, 0:header_section_width]

# Convert the header ROI to gray scale and threshold
gray_header = cv2.cvtColor(header_roi, cv2.COLOR_BGR2GRAY)
_, thresh_header = cv2.threshold(gray_header, 150, 255, cv2.THRESH_BINARY_INV)

# Find contours in the header ROI
contours_header, _ = cv2.findContours(thresh_header, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f'Number of contours found in the header: {len(contours_header)}')

# Filter contours found in the header based on size or other heuristics
contours_header = [cnt for cnt in contours_header if 0 < cv2.contourArea(cnt) < 50000]
print(f'Number of contours found in the header after filtering: {len(contours_header)}')

# Sort contours within the header from left to right
contours_header.sort(key=lambda x: cv2.boundingRect(x)[0])

def score_contour_position(x, y, w, h, image_width, image_height):
    # Define vertical margin as top 50% of the header height
    top_margin_end = image_height * 0.2

    # Define horizontal regions of the header: left, center, right
    left_region_end = image_width * 0.33
    right_region_start = image_width * 0.66

    # Initialize scores
    horizontal_score = 0
    vertical_score = 0

    # Assign horizontal scores based on region
    if x < left_region_end:
        horizontal_score = 1.0
    elif x > right_region_start:
        horizontal_score = 1.0
    else:
        horizontal_score = 0.5  # center region has a lower score

    # Assign vertical score based on the top margin
    if y < top_margin_end:
        vertical_score = 1.0  # higher score for top margin

    print(f'image: width={image_width}, height={image_height}')
    print(f'position: x={x}, y={y}, w={w}, h={h}', top_margin_end, left_region_end, right_region_start)
    print(f'scores: horizontal={horizontal_score}, vertical={vertical_score}')
    # Final score is a combination of horizontal and vertical scores
    return horizontal_score * vertical_score

def is_likely_logo_header(contour, image_width, image_height):
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = w / float(h)

    # Use the scoring function to give weight to the position
    position_score = score_contour_position(x, y, w, h, image_width, image_height)

    # Set a threshold score above which a contour is likely to be a logo
    position_score_threshold = 0.5

    # Check if the contour's position score meets the threshold
    is_position_likely = position_score > position_score_threshold

    # Check aspect ratio validity
    is_aspect_ratio_valid = 0.5 < aspect_ratio < 2
    print(f'aspect ratio: {aspect_ratio}, is_position_likely: {is_position_likely}, is_aspect_ratio_valid: {is_aspect_ratio_valid}')
    return is_position_likely and is_aspect_ratio_valid


# Now use this function when processing the header ROI contours

# Extract text or logo from each contour in the header
for cnt in contours_header:
    x, y, w, h = cv2.boundingRect(cnt)
    roi_header = header_roi[y:y+h, x:x+w]

    # Use the header-specific is_likely_logo function
    if is_likely_logo_header(cnt, header_section_width, header_section_height):
        # Save or process the logo image (roi_header)
        cv2.imwrite(os.path.join(logo_dir,f'logo_{x}_{y}.png'), roi_header)
        print(f'Logo saved: logo_{x}_{y}.png')
    else:
        # Apply OCR to the region of interest in the header
        text = pytesseract.image_to_string(roi_header, lang='eng', config='--psm 6')
        print(f'Extracted text: {text}')



def save_debug_image(image, output_path,countours_header):
    # Go through each contour in the header and draw rectangles around potential logos
    for cnt in contours_header:
        x, y, w, h = cv2.boundingRect(cnt)

        # Adjust y to account for the header's relative position
        adjusted_y = y  # Since we are working within the header ROI, y is already relative to the header

        # Check if the contour is likely a logo
        if is_likely_logo_header(cnt, header_section_width, header_section_height):
            # Draw a green rectangle around the likely logo
            cv2.rectangle(debug_image, (x, adjusted_y), (x + w, adjusted_y + h), (0, 255, 0), 2)
        else:
            # Draw a red rectangle around unlikely logos for contrast
            cv2.rectangle(debug_image, (x, adjusted_y), (x + w, adjusted_y + h), (0, 0, 255), 1)

    cv2.rectangle(debug_image, (0, 0), (header_section_width, header_section_height), (255, 0, 0), 2)
    cv2.rectangle(debug_image, (0, 0), (header_section_width, int(header_section_height * 0.2)), (255, 0, 0), 3)

    # Save the debug image with rectangles
    debug_header_image_path = os.path.join(logo_dir,'debug_header_image.png')
    cv2.imwrite(debug_header_image_path, debug_image)




# Create a copy of the original image to draw on for debugging
debug_image = image.copy()
save_debug_image(debug_image, "",contours_header)