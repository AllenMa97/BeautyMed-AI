# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import tempfile
from typing import Dict, List
import PyPDF2
from docx import Document
import pandas as pd
from PIL import Image
import pytesseract
import os

class DocumentProcessor:
    def __init__(self):
        # Initialize OCR engine
        self.ocr_engine = pytesseract
        
    async def process_file(self, file_path: str, mime_type: str = None) -> str:
        """
        Process a file based on its type and extract text content
        """
        if not mime_type:
            mime_type = self._get_mime_type(file_path)
        
        if mime_type.startswith('text/') or file_path.lower().endswith('.txt'):
            return await self._process_text_file(file_path)
        elif mime_type == 'application/pdf' or file_path.lower().endswith('.pdf'):
            return await self._process_pdf_file(file_path)
        elif (mime_type.startswith('application/vnd.openxmlformats-officedocument') or 
              file_path.lower().endswith(('.docx', '.doc'))):
            return await self._process_word_file(file_path)
        elif (mime_type.startswith('application/vnd.ms-excel') or 
              mime_type.startswith('application/vnd.openxmlformats-officedocument.spreadsheetml') or
              file_path.lower().endswith(('.xlsx', '.xls'))):
            return await self._process_excel_file(file_path)
        elif mime_type.startswith(('image/', 'image')):
            return await self._process_image_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
    
    def _get_mime_type(self, file_path: str) -> str:
        """Guess MIME type based on file extension"""
        ext = file_path.lower().split('.')[-1]
        mime_types = {
            'txt': 'text/plain',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    async def _process_text_file(self, file_path: str) -> str:
        """Process plain text files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def _process_pdf_file(self, file_path: str) -> str:
        """Process PDF files"""
        content = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        return content
    
    async def _process_word_file(self, file_path: str) -> str:
        """Process Word documents"""
        doc = Document(file_path)
        content = []
        for paragraph in doc.paragraphs:
            content.append(paragraph.text)
        return "\n".join(content)
    
    async def _process_excel_file(self, file_path: str) -> str:
        """Process Excel files"""
        # Read all sheets and convert to text
        excel_file = pd.ExcelFile(file_path)
        content = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            content.append(f"Sheet: {sheet_name}\n")
            content.append(df.to_string())
            content.append("\n")
        
        return "\n".join(content)
    
    async def _process_image_file(self, file_path: str) -> str:
        """Process image files using OCR"""
        # Use advanced OCR processor with vision-language model
        try:
            from .processors.ocr_processor import perform_ocr
            text = await perform_ocr(file_path)
            return text
        except ImportError:
            # Fallback to traditional OCR if new processor is not available
            image = Image.open(file_path)
            text = self.ocr_engine.image_to_string(image)
            return text