import os
import sys
from pathlib import Path
import logging
from typing import Optional

def setup_logging(log_file: Optional[str] = None) -> None:
    """Initialize logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file) if log_file else logging.StreamHandler()
        ]
    )

def main() -> None:
    """Main entry point for the application"""
    try:
        # Initialize logging
        setup_logging()
        
        logger = logging.getLogger(__name__)
        logger.info("Starting application...")
        
        # Your application logic here
        logger.info("Application initialized successfully")
        
    except Exception as e:
        logging.error(f"Application failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
