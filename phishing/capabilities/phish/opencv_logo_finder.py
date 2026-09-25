import cv2
import numpy as np
import os
from sklearn.cluster import KMeans
import pytesseract


def get_region_of_interest(viewport_x, viewport_y, viewport_width, viewport_height):
    # Define regions of interest (ROI) within the viewport for top left, top center, top right
    # Adjusting to consider only the top 20% of the viewport height and dividing the viewport width into thirds
    viewport_height_factor = 0.5
    roi_top_left = (viewport_x, viewport_y, viewport_width // 3, int(viewport_height * viewport_height_factor))
    roi_top_center = (viewport_x + viewport_width // 3, viewport_y, viewport_width // 3, int(viewport_height * viewport_height_factor))
    roi_top_right = (viewport_x + 2 * (viewport_width // 3), viewport_y, viewport_width // 3, int(viewport_height * viewport_height_factor))

    return roi_top_left, roi_top_center, roi_top_right

# Function to estimate the vividness/contrast of a contour
def contour_contrast_measure(cnt, hsv_image):
    mask = np.zeros(hsv_image.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [cnt], -1, 255, -1)
    mean_val = cv2.mean(hsv_image, mask=mask)
    # Simplified contrast measure: use the mean saturation and value as proxies for vividness
    return mean_val[1] + mean_val[2]  # Saturation + Value

def filter_boxes_by_text(boxes, image):
    filtered_boxes = []
    for box in boxes:
        x1, y1, x2, y2 = box
        cropped = image[y1:y2, x1:x2]
        try:
            text = pytesseract.image_to_string(cropped, config='--psm 6')
            word_count = len(text.split())
            if word_count <= 2:  # Adjust as necessary
                filtered_boxes.append(box)
        except (pytesseract.TesseractError, ValueError) as e:
            # If pytesseract throws an exception, add the box to filtered_boxes and continue
            print(f"pytesseract failed to process box: {box}")
            filtered_boxes.append(box)
    return filtered_boxes

def rank_boxes(box, hsv, roi_top_left, roi_top_center, roi_top_right):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    area = w * h

    # Assuming calculate_color_diversity and is_contour_in_roi can be adapted for boxes
    # For the sake of this example, let's focus on area and position (ROI checks will need adaptation)
    color_diversity = calculate_color_diversity_for_box(box, hsv)  # Adapted function for boxes

    # Prioritize by ROI (adapted checks for boxes)
    if is_box_in_roi_2(box, roi_top_left):
        priority = 0
    elif is_box_in_roi_2(box, roi_top_center):
        priority = 1
    elif is_box_in_roi_2(box, roi_top_right):
        priority = 2
    else:
        priority = 3  # Not in any top ROI

    #print(f"box: {box}, area: {area}, color_diversity: {color_diversity}, priority: {priority}")
    return (priority,x1,y1, -area, color_diversity)  # Adjusted to use box directly

def calculate_max_values(boxes,hsv):
    max_x = 0
    max_area = 0
    # Assuming calculate_color_diversity_for_box is defined and computes color diversity for a given box
    max_color_diversity = 0

    for box in boxes:
        x1, y1, x2, y2 = box
        area = (x2 - x1) * (y2 - y1)
        # For color diversity, you'll need to have the hsv image data accessible here
        color_diversity = calculate_color_diversity_for_box(box, hsv)  # Placeholder for actual calculation

        max_x = max(max_x, x1, x2)
        max_area = max(max_area, area)
        max_color_diversity = max(max_color_diversity, color_diversity)

    max_x = max(max_x, 1)  # Ensure a minimum value of 1
    max_area = max(max_area, 1)  # Ensure a minimum value of 1
    max_color_diversity = max(max_color_diversity, 1)
    return max_x, max_area, max_color_diversity


def rank_box_by_score(box, hsv, roi_top_left, roi_top_center, roi_top_right, max_x, max_area, max_color_diversity):

    print(f"box:{box}, hsv:{hsv}, roi_top_left:{roi_top_left}, roi_top_center:{roi_top_center}, roi_top_right:{roi_top_right}, max_x:{max_x}, max_area:{max_area}, max_color_diversity:{max_color_diversity}")

    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    area = w * h

    # Normalize x position to prioritize left-most boxes
    norm_x_position = 1 - (x1 / max_x)  # Assuming max_x is the width of the image or the max x1 value among all boxes

    # Normalize area
    norm_area = area / max_area  # Assuming max_area is calculated from all boxes

    # Calculate and normalize color diversity
    color_diversity = calculate_color_diversity_for_box(box, hsv)  # This needs to be defined
    norm_color_diversity = color_diversity / max_color_diversity  # Assuming max_color_diversity is calculated from all boxes

    # Adjust priority based on ROI
    if is_box_in_roi_2(box, roi_top_left):
        priority = 0
    elif is_box_in_roi_2(box, roi_top_center):
        priority = 1
    elif is_box_in_roi_2(box, roi_top_right):
        priority = 2
    else:
        priority = 3  # Not in any top ROI

    # Define weights for each component of the score
    w_position = 0.3  # Adjust as needed
    w_area = 0.3  # Adjust as needed
    w_color_diversity = 0.3  # Adjust as needed
    w_priority = 0.1  # Adjust as needed, ensuring it influences the final score

    # Composite score calculation
    composite_score = (w_position * norm_x_position) + (w_area * norm_area) + (w_color_diversity * norm_color_diversity) - (w_priority * priority)
    print(f"box: {box}, composite_score: {composite_score}")
    return composite_score


def is_box_in_roi_2(box, roi):
    x1, y1, x2, y2 = box
    roi_x, roi_y, roi_w, roi_h = roi
    # Check if the box is within the ROI (simple version, might need refinement)
    #return x1 >= roi_x and y1 >= roi_y #and x2 <= (roi_x + roi_w) and y2 <= (roi_y + roi_h)
    return x1 >= roi_x and y2 <= (roi_y + roi_h)

def calculate_color_diversity_for_box(box, hsv_image):
    x1, y1, x2, y2 = box

    # Create a mask for the current box
    mask = np.zeros(hsv_image.shape[:2], dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255

    # Extract the box's pixels in HSV space
    box_pixels_hsv = hsv_image[mask == 255]

    # Use clustering on the hue channel to quantify color diversity
    if len(box_pixels_hsv) > 1:  # Ensure there are pixels to analyze
        try:
            kmeans = KMeans(n_init='auto', n_clusters=2, random_state=0).fit(box_pixels_hsv[:, 0].reshape(-1, 1))
            # Variance within clusters can indicate diversity; lower variance = more distinct colors
            diversity_score = -np.var(kmeans.labels_)
            return diversity_score
        except Exception as e:
            print(f"KMeans failed with error: {str(e)}")
            return -np.inf  # or handle the exception in another appropriate way
    else:
        return -np.inf  # Minimally diverse if only one pixel or none

def merge_overlapping_boxes_2(boxes, merge_threshold=10):
    if len(boxes) == 0:
        return []

    # Convert to list for mutability
    boxes = [list(box) for box in boxes]
    merged_boxes = []

    while boxes:
        main_box = boxes.pop(0)
        merged_box = main_box.copy()
        changed = True

        while changed:
            changed = False
            for i in range(len(boxes) - 1, -1, -1):
                other_box = boxes[i]
                # Check if boxes are horizontally close (within threshold)
                horizontally_close = (other_box[2] >= merged_box[0] - merge_threshold and other_box[0] <= merged_box[2] + merge_threshold)
                # Check for vertical overlap
                vertical_overlap = not (other_box[3] < merged_box[1] - merge_threshold or other_box[1] > merged_box[3] + merge_threshold)

                if horizontally_close and vertical_overlap:
                    # Merge the boxes
                    merged_box[0] = min(merged_box[0], other_box[0])
                    merged_box[1] = min(merged_box[1], other_box[1])
                    merged_box[2] = max(merged_box[2], other_box[2])
                    merged_box[3] = max(merged_box[3], other_box[3])
                    boxes.pop(i)
                    changed = True

        merged_boxes.append(tuple(merged_box))

    return np.array(merged_boxes).astype("int")


def process_image(image_path, output_directory):
    # Read in the image
    image = cv2.imread(image_path)
    image_height, image_width, _ = image.shape

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Example viewport coordinates and dimensions
    viewport_x = 10  # X coordinate of the viewport's top-left corner
    viewport_y = 50   # Y coordinate of the viewport's top-left corner
    viewport_width = image_width  # Width of the viewport
    viewport_height = 600 if image_height > 600 else image_height  # Height of the viewport

    roi_top_left, roi_top_center, roi_top_right = get_region_of_interest(viewport_x, viewport_y, viewport_width, viewport_height)

    # Convert to grayscale and apply Gaussian blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edges = cv2.Canny(blurred, 100, 200)

    # Use morphology to close gaps between edge segments
    kernel = np.ones((5,5), np.uint8)
    closing = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Find contours on the closed image
    contours, _ = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter the contours
    rectangles = [cv2.boundingRect(cnt) for cnt in contours if cv2.contourArea(cnt) > 10]
    # Add margin and adjust format to [x1, y1, x2, y2]
    margin = 10
    rectangles_with_margin = [[x-margin, y-margin, x+w+margin, y+h+margin] for x, y, w, h in rectangles]

    # Function to merge rectangles (as previously defined)
    merged_boxes = merge_overlapping_boxes_2(np.array(rectangles_with_margin))
    filtered_boxes = filter_boxes_by_text(merged_boxes, image)
    (max_x, max_area, max_color_diversity) = calculate_max_values(filtered_boxes,hsv)

    def sort_key_wrapper(box):
        #return rank_box_by_score(box, hsv, roi_top_left, roi_top_center, roi_top_right, max_x, max_area, max_color_diversity)
        return rank_boxes(box, hsv, roi_top_left, roi_top_center, roi_top_right)

    sorted_boxes = sorted(filtered_boxes, key=sort_key_wrapper)

    # Drawing and numbering sorted and filtered boxes
    debug_image = image.copy()
    for i, (x1, y1, x2, y2) in enumerate(rectangles_with_margin):
        cv2.rectangle(debug_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(debug_image, f"#{i+1}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Construct the output path
    output_path = os.path.join(output_directory, 'processed_' + os.path.basename(image_path))

    cv2.imwrite(output_path, debug_image)

    return output_path


def process_batch(input_directory,output_directory):
    #input_directory = '/path/to/input/directory'  # Replace with the path to your input directory
    #output_directory = '/path/to/output/directory'  # Replace with the path to your output directory

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Iterate over all files in the input directory
    for filename in os.listdir(input_directory):
        # Check if the file is an image (you can add more file types if needed)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Construct the full path to the image
            image_path = os.path.join(input_directory, filename)
            print(f"Processing image: {image_path}")
            # Process the image
            output_path = process_image(image_path, output_directory)

            # Construct the output path
            #output_path = os.path.join(output_directory, 'processed_' + filename)

            # Save the processed image to the output directory
            #os.rename(cropped_header_image_path, output_path)

            print(f"Processed image saved to: {output_path}")

def process_one(input_image_path, output_directory):

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Process the image
    output_path = process_image(input_image_path, output_directory)

    print(f"Processed image saved to: {output_path}")

if __name__ == "__main__":
    input_dir = "/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets-normal"
    output_dir = "/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/extracted_logos_score"
    #process_batch(input_dir, output_dir)
    input_image_path = "/Users/sandeep/Documents/SB_Sources/anm_dintel/cortex/temp-assets-normal/da07579b-ef90-463e-b574-28fa9d0fbe35.png"
    process_one(input_image_path, output_dir)