#django command using gpt-3

from django.core.management.base import BaseCommand, CommandParser
from capabilities.phish.scanner import openai_vision_summarize
import csv
import os
import sqlite3
from typing import Optional, Union, Dict
from pydantic import BaseModel
from pprint import pprint

class WebPageDesc(BaseModel):
    url: Optional[str]
    screenshot_path: Optional[str]
    content_path: Optional[str]
    error: Optional[str]
    target: Optional[str]
    is_phish: Optional[bool]
    source: Optional[str]
    brand: Optional[str]
    brand_url: Optional[str]
    business_category: Optional[str]
    webpage_summary: Optional[str]
    cta: Optional[str]  # Call to Action
    contact_info: Optional[Union[str, Dict]]
    language: Optional[str]

def process_file(file_path, db_path, start_row=0, limit=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS web_page_desc (
            url TEXT,
            screenshot BLOB,
            content TEXT,
            error TEXT,
            target TEXT,
            is_phish BOOLEAN,
            source TEXT,
            brand TEXT,
            brand_url TEXT,
            business_category TEXT,
            webpage_summary TEXT,
            cta TEXT,
            contact_info TEXT,
            language TEXT,
            screenshot_path TEXT,
            content_path TEXT,
            evaluator TEXT,
            PRIMARY KEY (url, evaluator)
        )
    ''')
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for _ in range(start_row):  # Skip rows up to start_row
            next(reader, None)
        for i, row in enumerate(reader, start_row):
            if limit and i >= start_row + limit:  # Stop processing rows after limit
                break
            if row and os.path.exists(row[1]):  # Check if the screenshot file exists
                with open(row[1], 'rb') as screenshot_file, open(row[2], 'r') as content_file:  # Open the screenshot and content files
                    screenshot = screenshot_file.read()  # Read the screenshot as binary data
                    content = content_file.read()  # Read the content as text
                result = openai_image_summarize(row[1])  # Pass the screenshot path to the openai_image_summarize function
                if result:
                    web_page_desc = WebPageDesc(url=row[0], screenshot_path=screenshot, content_path=content, error=row[3], target=row[4], is_phish=row[5], source='source', **result)
                    cursor.execute('''
                        INSERT INTO web_page_desc (
                            url,
                            screenshot,
                            content,
                            error,
                            target,
                            is_phish,
                            source,
                            brand,
                            brand_url,
                            business_category,
                            webpage_summary,
                            cta,
                            contact_info,
                            language,
                            screenshot_path,
                            content_path,
                            evaluator
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?, ?)
                    ''', (
                        web_page_desc.url,
                        web_page_desc.screenshot,
                        web_page_desc.content,
                        web_page_desc.error,
                        web_page_desc.target,
                        web_page_desc.is_phish,
                        web_page_desc.source,
                        web_page_desc.brand,
                        web_page_desc.brand_url,
                        web_page_desc.business_category,
                        web_page_desc.webpage_summary,
                        web_page_desc.cta,
                        web_page_desc.contact_info,
                        web_page_desc.language,
                        web_page_desc.screenshot_path,
                        web_page_desc.content_path,
                        'GPT4-Vision'
                    ))
    conn.commit()
    conn.close()

class Command(BaseCommand):
    help = 'Evaluate using GPT-3'

    def add_arguments(self, parser: CommandParser) -> None:
       # parser.add_argument('-f','--file', type=str, help='Path to the file')
        parser.add_argument('-f','--file', type=str, help='Path to the file')

    def handle(self, *args, **options):
        file = options['file']
        print(f'file: {file}')
        result = openai_vision_summarize(file)
        pprint(result) 