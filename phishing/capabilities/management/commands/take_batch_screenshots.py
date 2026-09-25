# django management command to take batch screenshots of a list of urls

import os
import time
import requests
import csv
import concurrent.futures
from tqdm import tqdm

from django.core.management.base import BaseCommand
from capabilities.phish.scanner import take_screenshot
from urllib.parse import urlparse

def parse_file_serial(file_path, output_file_path, screenshot_output_dir, seccomp_path, start_row=0,limit=100):
        with open(file_path, 'r') as file, open(output_file_path, 'w', newline='') as output_file:
            reader = csv.reader(file)
            writer = csv.writer(output_file)
            writer.writerow(['url', 'screenshot_path', 'content_path', 'error','target', 'is_phish'])  # Write the header
            next(reader, None)  # Skip the header
            rows = list(reader)  # Convert the reader to a list to get the total number of rows
            successful_screenshots = 0
            progress_bar = tqdm(total=limit, desc="Processing", unit="screenshots")  # Initialize the progress bar
            for row in rows[start_row:]:  # Wrap the iterable with tqdm
                if successful_screenshots >= limit:
                    break
                if row:
                    if len(row) == 1:  # If the row has only one element (a URL)
                        url = row[0]
                        target = 'unknown'
                    else:  # If the row has more elements
                        phish_id, url, phish_detail_url, submission_time, verified, verification_time, online, target = row

                    #phish_id, url, phish_detail_url, submission_time, verified, verification_time, online, target = row

                    time_start = time.time()
                    url_parsed = urlparse(url)
                    if not url_parsed.scheme:
                        url = 'https://' + url

                    print(f'Processing {url}')
                    result = take_screenshot(url,screenshot_output_dir, seccomp_path)
                    if result['screenshot_path'] and result['source_path'] and os.path.exists(result['screenshot_path']):
                        writer.writerow([url, result['screenshot_path'], result['source_path'], result['error'],target, 'true'])
                        print(f'Screenshot and source saved for {url}')
                        successful_screenshots += 1
                        time_end = time.time()
                        progress_bar.set_postfix({'time_elapsed': f'{time_end - time_start:.2f}s'}, refresh=True)
                        progress_bar.update(1)
                    else:
                        print(f'Failed to take screenshot or save source for {url}')

# python manage.py take_batch_screenshots -f online-valid.csv -o screenshot_results_batch_2.csv -d ./temp-assets/ -c seccomp_profile.json -s 101 -l 50
class Command(BaseCommand):
    help = 'Take batch screenshots of a list of urls'

    def add_arguments(self, parser):
        parser.add_argument('-f','--phishtank_export_csv_file', type=str, help='Path to the phishtank export csv file')
        parser.add_argument('-d','--screenshot_output_dir', help='Directory to save screenshot')
        parser.add_argument('-c','--seccomp_path', help='Path to seccomp profile')
        parser.add_argument('-o','--output_file', type=str, help='Output file path')
        parser.add_argument('-l','--limit', type=int, help='Limit the number of screenshots to take',default=100)
        parser.add_argument('-s','--start_row', type=int, help='Start row to begin processing', default=0)


    def process_row(self, row):
        phish_id, url, phish_detail_url, submission_time, verified, verification_time, online, target = row
        print(f'Processing {url}')
        result = self.take_screenshot(url)
        if result['screenshot_path'] and result['source_path']:
            return [url, result['screenshot_path'], result['source_path'], target, 'true']
        else:
            print(f'Failed to take screenshot or save source for {url}')
            return None

    def parse_file(self, file_path, output_file_path, limit=100):
        with open(file_path, 'r') as file, open(output_file_path, 'w', newline='') as output_file:
            reader = csv.reader(file)
            writer = csv.writer(output_file)
            writer.writerow(['url', 'screenshot_path', 'content_path', 'target', 'is_phish'])  # Write the header
            next(reader, None)  # Skip the header

            successful_screenshots = 0
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_row = {executor.submit(self.process_row, row): row for row in reader}
                for future in concurrent.futures.as_completed(future_to_row):
                    if successful_screenshots >= limit:
                        break
                    row = future_to_row[future]
                    try:
                        result = future.result()
                        if result and result[1]:  # Check if screenshot_path is not None
                            writer.writerow(result)
                            successful_screenshots += 1
                    except Exception as exc:
                        print(f'Generated an exception: {exc}')

    def handle(self, *args, **kwargs):
        stime = time.time()

        parse_file_serial(  kwargs['phishtank_export_csv_file'],
                                kwargs['output_file'],
                                kwargs['screenshot_output_dir'],
                                kwargs['seccomp_path'],
                                start_row=kwargs['start_row'],
                                limit=kwargs['limit']
                            )

        print(f'### Processing time: {time.time() - stime:.2f}s')