# backend/services/document_processor.py - EXTRACT TEXT FROM DOCUMENTS

import PyPDF2
from pathlib import Path
from config.logging_config import logger

class DocumentProcessor:
    """Process documents and extract text"""
    
    async def process_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            logger.info(f"📄 Extracting text from PDF: {file_path}")
            
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text += page.extract_text() + "\n\n"
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to extract page {page_num}: {e}")
            
            if not text.strip():
                raise ValueError("No text could be extracted from PDF")
            
            logger.info(f"✅ Extracted {len(text)} characters from PDF")
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ PDF processing error: {e}")
            raise
    
    async def process_text(self, file_path: str) -> str:
        """
        Read text file
        
        Args:
            file_path: Path to text file
            
        Returns:
            File content
        """
        try:
            logger.info(f"📄 Reading text file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            logger.info(f"✅ Read {len(text)} characters from file")
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ Text file processing error: {e}")
            raise
