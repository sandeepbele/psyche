# django management command to take batch screenshots
# import os
from django.core.management.base import BaseCommand, CommandParser
import csv
import os

def merge_files(file1_path, file2_path, merged_file_path):
    with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2, open(merged_file_path, 'w', newline='') as merged_file:
        reader1 = csv.reader(file1)
        reader2 = csv.reader(file2)
        writer = csv.writer(merged_file)
        writer.writerow(['url', 'screenshot_path', 'content_path', 'error','target', 'is_phish'])  # Write the header
        for row in reader1:
            if row and os.path.exists(row[1]):  # Check if the screenshot file exists
                writer.writerow(row)
        for row in reader2:
            if row and os.path.exists(row[1]):  # Check if the screenshot file exists
                writer.writerow(row)


class Command(BaseCommand):

# python manage.py merge_screenshot_results -f1 screenshot_results_batch_1.csv -f2 screenshot_results_batch_2.csv -o screenshot_merged.csv

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('-f1','--file1', type=str, help='Path to the first file')
        parser.add_argument('-f2','--file2', type=str, help='Path to the second file')
        parser.add_argument('-o','--output_file', type=str, help='Output file path')

    def handle(self, *args, **options):
        file1 = options['file1']
        file2 = options['file2']
        print(f'file1: {file1}')
        print(f'file2: {file2}')

        merge_files(file1, file2, options['output_file'])

