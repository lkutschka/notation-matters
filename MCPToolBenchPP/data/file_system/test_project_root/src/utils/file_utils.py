import os
import shutil
import hashlib
from pathlib import Path
from typing import Union, List, Optional

def read_file(file_path: Union[str, Path]) -> str:
    """Read content from a text file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Content of the file as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If there are permission issues
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path: Union[str, Path], content: str, overwrite: bool = False) -> None:
    """Write content to a file.
    
    Args:
        file_path: Path to write to
        content: Content to write
        overwrite: Whether to overwrite existing file
        
    Raises:
        FileExistsError: If file exists and overwrite=False
        IOError: For permission issues
    """
    if os.path.exists(file_path) and not overwrite:
        raise FileExistsError(f"File {file_path} already exists")
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def get_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """Calculate file hash.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hex digest of file content
    """
    hash_func = getattr(hashlib, algorithm)()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def ensure_dir_exists(dir_path: Union[str, Path]) -> None:
    """Ensure directory exists, create if not.
    
    Args:
        dir_path: Path to directory
    """
    os.makedirs(dir_path, exist_ok=True)

def list_files(dir_path: Union[str, Path], recursive: bool = False) -> List[str]:
    """List files in directory.
    
    Args:
        dir_path: Directory to scan
        recursive: Whether to scan recursively
        
    Returns:
        List of file paths
    """
    if recursive:
        return [os.path.join(root, f) 
                for root, _, files in os.walk(dir_path) 
                for f in files]
    return [f for f in os.listdir(dir_path) 
            if os.path.isfile(os.path.join(dir_path, f))]

def safe_delete(file_path: Union[str, Path]) -> bool:
    """Safely delete a file if it exists.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file was deleted, False if it didn't exist
    """
    try:
        os.remove(file_path)
        return True
    except FileNotFoundError:
        return False

def copy_file(src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> None:
    """Copy file from source to destination.
    
    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing file
        
    Raises:
        FileExistsError: If destination exists and overwrite=False
    """
    if os.path.exists(dst) and not overwrite:
        raise FileExistsError(f"File {dst} already exists")
    shutil.copy2(src, dst)

def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)

def is_same_file(file1: Union[str, Path], file2: Union[str, Path]) -> bool:
    """Check if two files are identical by comparing hashes.
    
    Args:
        file1: First file path
        file2: Second file path
        
    Returns:
        True if files have same content
    """
    return get_file_hash(file1) == get_file_hash(file2)
