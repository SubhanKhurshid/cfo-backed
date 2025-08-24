from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import os
from pathlib import Path
import shutil
from typing import Dict, Any, Optional, List
import uvicorn
import logging

# Import our existing financial analysis functions
from api import (
    read_financial_file, 
    analyze_financial_data, 
    detect_file_type,
    read_csv_file  # We'll add this function
)

# Import Pinecone integration and chatbot
from pinecone_manager import get_pinecone_manager
from chatbot_service import get_financial_chatbot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI CFO Financial Analysis & Chatbot API",
    description="Upload financial documents (CSV, XLSX, XLS, PDF) and get comprehensive financial analysis including P&L, Balance Sheet, Cash Flow, and AR/AP Aging reports. Features an intelligent chatbot for querying your financial data using natural language.",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-cfo-assistant.vercel.app",  # your Vercel frontend
        "http://localhost:3000",  # for local dev (optional)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI CFO Financial Analysis & Chatbot API",
        "description": "Upload financial documents for comprehensive analysis and chat with AI about your financial data",
        "supported_formats": ["CSV", "XLSX", "XLS", "PDF"],
        "main_endpoints": {
            "single_upload": "/upload-financial-document",
            "multi_upload": "/analyze-multiple-files",
            "chat": "/chat",
            "health": "/health"
        },
        "chatbot_endpoints": {
            "chat": "/chat",
            "delete_document": "/document/{document_id}",
            "chatbot_health": "/health/chatbot"
        },
        "features": [
            "Financial document analysis",
            "AI-powered chatbot for financial queries",
            "Vector database storage for intelligent search",
            "Multi-document support",
            "Real-time financial insights"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CFO Financial Analysis API"}

@app.post("/upload-financial-document")
async def upload_financial_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Query(None, description="User ID for document association"),
    store_in_vector_db: bool = Query(True, description="Whether to store analysis in vector database for chatbot")
):
    """
    Upload a financial document and get comprehensive analysis
    
    Supported formats: CSV, XLSX, XLS, PDF
    Returns: JSON with P&L, Balance Sheet, Cash Flow, and AR/AP Aging analysis
    Optionally stores analysis in vector database for chatbot functionality
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
        
        # Prepare file info
        file_info = {
            "filename": file.filename,
            "file_type": file_type,
            "file_size_mb": round(file_size / (1024*1024), 2)
        }
        
        # Store in vector database if requested
        document_id = None
        if store_in_vector_db:
            try:
                pinecone_manager = get_pinecone_manager()
                document_id = pinecone_manager.store_financial_data(
                    financial_analysis=analysis_result,
                    file_info=file_info,
                    user_id=user_id
                )
                logger.info(f"Stored document {file.filename} in vector database with ID: {document_id}")
            except Exception as e:
                logger.error(f"Failed to store in vector database: {str(e)}")
                # Don't fail the entire request if vector storage fails
        
        # Add metadata to response
        response_data = {
            "file_info": file_info,
            "analysis": analysis_result,
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
async def analyze_multiple_files(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = Query(None, description="User ID for document association"),
    store_in_vector_db: bool = Query(True, description="Whether to store analysis in vector database for chatbot")
):
    """
    Upload multiple financial documents and get combined analysis
    
    Supported formats: CSV, XLSX, XLS, PDF
    Returns: JSON with analysis for each file plus combined insights
    Optionally stores analysis in vector database for chatbot functionality
    """
    
    if len(files) > 10:  # Limit to 10 files
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum 10 files allowed per request."
        )
    
    results = {}
    temp_files = []
    document_ids = []
    
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
                    file_info = {
                        "filename": file.filename,
                        "file_type": file_type,
                        "file_size_mb": round(file_size / (1024*1024), 2)
                    }
                    
                    # Store in vector database if requested
                    document_id = None
                    if store_in_vector_db:
                        try:
                            pinecone_manager = get_pinecone_manager()
                            document_id = pinecone_manager.store_financial_data(
                                financial_analysis=analysis_result,
                                file_info=file_info,
                                user_id=user_id
                            )
                            document_ids.append(document_id)
                            logger.info(f"Stored document {file.filename} in vector database with ID: {document_id}")
                        except Exception as e:
                            logger.error(f"Failed to store {file.filename} in vector database: {str(e)}")
                            # Don't fail the entire request if vector storage fails
                    
                    results[file.filename] = {
                        "file_info": file_info,
                        "analysis": analysis_result,
                    }
        
        return JSONResponse(content={
            "files_processed": len(results),
            "results": results,
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

# ================================
# CHATBOT ENDPOINTS
# ================================

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    conversation_history: Optional[List[Dict]] = None

@app.post("/chat")
async def chat_with_financial_data(request: ChatRequest):
    """
    Chat with AI about uploaded financial documents
    
    Send a question about your financial data and get intelligent responses
    based on previously uploaded and analyzed documents.
    """
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )
        
        # Get chatbot instance
        chatbot = get_financial_chatbot()
        
        # Process the chat request
        response = chatbot.chat(
            user_message=request.message.strip(),
            user_id=request.user_id,
            conversation_history=request.conversation_history or []
        )
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )

# Document management endpoints removed - now handled by frontend PostgreSQL integration

@app.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Query(..., description="User ID")
):
    """
    Delete a financial document and all its associated data
    """
    try:
        pinecone_manager = get_pinecone_manager()
        success = pinecone_manager.delete_document(document_id, user_id)
        
        if success:
            return JSONResponse(content={
                "message": f"Document {document_id} deleted successfully",
                "document_id": document_id
            })
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found for user {user_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

@app.get("/health/chatbot")
async def chatbot_health_check():
    """Health check for chatbot and vector database connectivity"""
    try:
        # Test Pinecone connection
        pinecone_manager = get_pinecone_manager()
        
        # Test OpenAI connection
        chatbot = get_financial_chatbot()
        
        return JSONResponse(content={
            "status": "healthy",
            "services": {
                "pinecone": "connected",
                "openai": "connected",
                "chatbot": "operational"
            }
        })
        
    except Exception as e:
        logger.error(f"Chatbot health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "services": {
                    "pinecone": "error",
                    "openai": "error",
                    "chatbot": "unavailable"
                }
            }
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
