from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
from pathlib import Path
import shutil
from typing import Dict, Any
import uvicorn

# Import our existing financial analysis functions
from api import (
    read_financial_file, 
    analyze_financial_data, 
    detect_file_type,
    read_csv_file  # We'll add this function
)

app = FastAPI(
    title="CFO Financial Analysis API",
    description="Upload financial documents (CSV, XLSX, PDF) and get comprehensive financial analysis including P&L, Balance Sheet, Cash Flow, and AR/AP Aging reports",
    version="1.0.0"
)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "CFO Financial Analysis API",
        "description": "Upload financial documents for comprehensive analysis",
        "supported_formats": ["CSV", "XLSX", "XLS", "PDF"],
        "endpoints": {
            "upload": "/upload-financial-document",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CFO Financial Analysis API"}

@app.post("/upload-financial-document")
async def upload_financial_document(file: UploadFile = File(...)):
    """
    Upload a financial document and get comprehensive analysis
    
    Supported formats: CSV, XLSX, XLS, PDF
    Returns: JSON with P&L, Balance Sheet, Cash Flow, and AR/AP Aging analysis
    """
    
    # Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size allowed: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Create temporary file
    temp_dir = tempfile.mkdtemp()
    temp_file_path = None
    
    try:
        # Save uploaded file to temporary location
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the file based on type
        financial_data, file_type = read_financial_file(temp_file_path)
        
        if financial_data is None:
            raise HTTPException(
                status_code=400,
                detail="Failed to parse the uploaded file. Please check the file format and content."
            )
        
        # Analyze the financial data
        analysis_result = analyze_financial_data(financial_data, file_type)
        
        if "error" in analysis_result:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {analysis_result['error']}"
            )
        
        # Add metadata to response
        response_data = {
            "file_info": {
                "filename": file.filename,
                "file_type": file_type,
                "file_size_mb": round(file_size / (1024*1024), 2)
            },
            "analysis": analysis_result
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
    finally:
        # Clean up temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass

@app.post("/analyze-multiple-files")
async def analyze_multiple_files(files: list[UploadFile] = File(...)):
    """
    Upload multiple financial documents and get combined analysis
    
    Supported formats: CSV, XLSX, XLS, PDF
    Returns: JSON with analysis for each file plus combined insights
    """
    
    if len(files) > 10:  # Limit to 10 files
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum 10 files allowed per request."
        )
    
    results = {}
    temp_files = []
    
    try:
        for file in files:
            # Validate each file
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format in {file.filename}. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Check file size
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
                )
            
            # Save to temporary file
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, file.filename)
            temp_files.append(temp_file_path)
            
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Process the file
            financial_data, file_type = read_financial_file(temp_file_path)
            
            if financial_data is not None:
                analysis_result = analyze_financial_data(financial_data, file_type)
                
                if "error" not in analysis_result:
                    results[file.filename] = {
                        "file_info": {
                            "file_type": file_type,
                            "file_size_mb": round(file_size / (1024*1024), 2)
                        },
                        "analysis": analysis_result
                    }
        
        return JSONResponse(content={
            "files_processed": len(results),
            "results": results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    # Try to remove the directory as well
                    temp_dir = os.path.dirname(temp_file)
                    os.rmdir(temp_dir)
            except:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
