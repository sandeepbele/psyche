import cv2
import numpy as np
import os , pytesseract

# Read in the image
#image_path = '/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets/3d7d3dee-7398-41ec-abdd-e33ece52fe44.png'
image_path = '/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/url_screenshots/c49c9c9e-55bc-4344-8ee2-b1fee088016c.png'
image = cv2.imread(image_path)

# Define the header section as a percentage of the page height, say the top 25%
header_section_height = int(image.shape[0] * 0.25)
header_section_width = image.shape[1]

# The header ROI is the slice of the image from the top down to the defined height
header_roi = image[0:header_section_height, 0:header_section_width]

# Convert to grayscale and apply Gaussian blur
gray = cv2.cvtColor(header_roi, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Edge detection
edges = cv2.Canny(blurred, 100, 200)

# Use morphology to close gaps between edge segments
kernel = np.ones((5,5), np.uint8)
closing = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

# Find contours on the closed image
contours, _ = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Filter the contours
contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 100]


#Define a function to calculate a sorting key for each contour
def sort_key(cnt):
    x, y, w, h = cv2.boundingRect(cnt)
    # Use a large multiplier for 'y' to ensure vertical position has priority
    #return y * 1000 + x
    # Prioritize x but also consider y to break ties for items with similar x values
    return x + y * 0.1  # The multiplier for y is small to ensure it has less weight than x

# Adjust the sort key function to prioritize y first, then x
def sort_key_for_top_then_left(cnt):
    x, y, w, h = cv2.boundingRect(cnt)
    # Return a tuple that Python will use for comparison, prioritizing y over x
    return y,x

# Sort contours by the defined key (top-left to bottom-right)
contours_sorted = sorted(contours, key=sort_key_for_top_then_left)

# Sort the contours by area, descending
#contours.sort(key=cv2.contourArea, reverse=True)

current_dir = os.getcwd()
logo_dir = os.path.join(current_dir, 'extracted_logos')

cropped_header_image_path = os.path.join(logo_dir,'cropped_header_image.png')
cv2.imwrite(cropped_header_image_path, header_roi)

def save_logo_image(logo_roi, output_path):
    # Add a margin to the logo ROI
    margin = 10  # Margin size in pixels
    height, width = logo_roi.shape[:2]
    logo_with_margin = cv2.copyMakeBorder(logo_roi, margin, margin, margin, margin, cv2.BORDER_CONSTANT, value=[255, 255, 255])

    # Scale the logo (example: scaling by 1.5 times)
    scale_factor = 2
    width_scaled = int(width * scale_factor)
    height_scaled = int(height * scale_factor)
    logo_scaled = cv2.resize(logo_with_margin, (width_scaled, height_scaled), interpolation=cv2.INTER_NEAREST_EXACT)

    # Save the processed logo
    #processed_logo_path = '/mnt/data/processed_logo.png'
    cv2.imwrite(output_path, logo_scaled)

if contours_sorted:
    # Get the first contour
    for i,candidate in enumerate(contours_sorted[:3]):

        # Extract the ROI for the first contour
        x, y, w, h = cv2.boundingRect(candidate)
        logo_roi = image[y:y+h, x:x+w]

        # Save the ROI as an image
        logo_image_path = os.path.join(logo_dir,f'extracted_logo_{i}.png')
        #cv2.imwrite(logo_image_path, logo_roi)
        save_logo_image(logo_roi, logo_image_path)

        logo_image_path
else:
    print("No contours found")

def merge_overlapping_boxes(boxes):
    if len(boxes) == 0:
        return []

    boxes = [list(box) for box in boxes]
    merged_boxes = []

    while len(boxes) > 0:
        main_box = boxes[0]

        boxes = boxes[1:]
        merged_box = main_box
        changed = True

        while changed:
            changed = False
            for other_box in boxes:
                if (other_box[0] <= merged_box[2] and other_box[2] >= merged_box[0] and
                    other_box[1] <= merged_box[3] and other_box[3] >= merged_box[1]):
                    merged_box[0] = min(merged_box[0], other_box[0])
                    merged_box[1] = min(merged_box[1], other_box[1])
                    merged_box[2] = max(merged_box[2], other_box[2])
                    merged_box[3] = max(merged_box[3], other_box[3])
                    boxes.remove(other_box)
                    changed = True

        merged_boxes.append(tuple(merged_box))

    return np.array(merged_boxes).astype("int")

def save_debug_image(image, output_path,countours_header):
    rectangles = []
    # Go through each contour in the header and draw rectangles around potential logos
    for i, cnt in enumerate(countours_header):
        x, y, w, h = cv2.boundingRect(cnt)

        # Adjust y to account for the header's relative position
        adjusted_y = y  # Since we are working within the header ROI, y is already relative to the header
        margin = 10
        # Add the rectangle to the list
        rectangles.append([x-margin, adjusted_y-margin, x + w+margin, adjusted_y + h+margin])

    # Group overlapping rectangles
    #rectangles, weights = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.01)
    # Merge overlapping rectangles
    rectangles = merge_overlapping_boxes(np.array(rectangles))

    # Draw the rectangles
    for rect in rectangles:
        cv2.rectangle(debug_image, (rect[0], rect[1]), (rect[2], rect[3]), (0, 255, 0), 1)    # Save the debug image with rectangles

    debug_header_image_path = os.path.join(logo_dir,'debug_header_image.png')
    cv2.imwrite(debug_header_image_path, debug_image)

    for rect in rectangles:
        # Ensure the rectangle is within the image's boundaries
        rect[0] = max(0, rect[0])
        rect[1] = max(0, rect[1])
        rect[2] = min(image.shape[1], rect[2])
        rect[3] = min(image.shape[0], rect[3])

        cv2.rectangle(image, (rect[0], rect[1]), (rect[2], rect[3]), (0, 255, 0), 1)

        # Crop the rectangle from the image and run OCR on it
        cropped = image[rect[1]:rect[3], rect[0]:rect[2]]
        text = pytesseract.image_to_string(cropped)
        print(text)

# Create a copy of the original image to draw on for debugging
debug_image = image.copy()
save_debug_image(debug_image, "",contours_sorted[:3])