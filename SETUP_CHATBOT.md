# AI CFO Chatbot Setup Guide

This guide will help you set up the AI-powered chatbot functionality for your CFO Financial Analysis API.

## Prerequisites

1. **OpenAI API Key**: Required for AI analysis, chat responses, and generating embeddings
2. **Pinecone API Key**: Required for vector database storage

## Environment Variables Setup

Create a `.env` file in the backend directory with the following variables:

```bash
# OpenAI API Configuration (for chat responses, analysis, and embeddings)
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Vector Database Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
```

### Getting API Keys

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key and add it to your `.env` file

#### Pinecone API Key
1. Go to [Pinecone Console](https://app.pinecone.io/)
2. Sign in or create an account
3. Navigate to "API Keys" in the sidebar
4. Copy your API key and add it to your `.env` file



## Installation

1. Install the dependencies:
```bash
pip install -r requirements.txt
```

2. The system will automatically create a Pinecone index named `financial-documents` when first started.

## New API Endpoints

### File Upload with Vector Storage
- **Single File**: `POST /upload-financial-document?user_id=USER_ID&store_in_vector_db=true`
- **Multiple Files**: `POST /analyze-multiple-files?user_id=USER_ID&store_in_vector_db=true`

### Chatbot Endpoints
- **Chat**: `POST /chat?message=YOUR_QUESTION&user_id=USER_ID`
- **Get Documents**: `GET /documents?user_id=USER_ID`
- **Document Summary**: `GET /document-summary?user_id=USER_ID`
- **Suggested Questions**: `GET /suggested-questions?user_id=USER_ID`
- **Delete Document**: `DELETE /document/{document_id}?user_id=USER_ID`
- **Health Check**: `GET /health/chatbot`

## Usage Examples

### 1. Upload a Financial Document
```bash
curl -X POST "http://localhost:8000/upload-financial-document?user_id=user123&store_in_vector_db=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_financial_document.xlsx"
```

### 2. Chat About Your Data
```bash
curl -X POST "http://localhost:8000/chat?message=What is my total revenue?&user_id=user123"
```

### 3. Get Suggested Questions
```bash
curl -X GET "http://localhost:8000/suggested-questions?user_id=user123"
```

### 4. Get Document List
```bash
curl -X GET "http://localhost:8000/documents?user_id=user123"
```

## Features

### Document Analysis & Storage
- Automatically extracts and analyzes financial data from uploaded documents
- Stores analysis results in Pinecone vector database for intelligent search
- Uses OpenAI text-embedding-3-small model for generating embeddings (1536 dimensions)
- Supports CSV, XLSX, XLS, and PDF file formats
- Chunks data into relevant sections (P&L, Balance Sheet, Cash Flow, etc.)

### AI Chatbot
- Natural language queries about your financial data
- Context-aware responses based on uploaded documents
- Suggested questions based on available data
- Multi-document support for comprehensive analysis

### Vector Database Features
- Semantic search across all financial documents using OpenAI embeddings
- User-specific data isolation
- Fast retrieval of relevant financial information
- Support for complex financial queries
- High-quality embeddings with OpenAI's latest models

## Data Organization

The system organizes your financial data into the following chunks:
- **Executive Summary**: Key insights and business health metrics
- **Profit & Loss**: Revenue, expenses, and profitability analysis
- **Balance Sheet**: Assets, liabilities, and equity information
- **Cash Flow**: Operating, investing, and financing activities
- **Financial Ratios**: Key performance indicators and ratios
- **Strategic Recommendations**: AI-generated business recommendations
- **AI Insights**: Trend analysis, anomaly detection, and predictions

## Security & Privacy

- Each user's data is isolated using user_id filtering
- Documents can be deleted individually
- All data is encrypted in transit and at rest
- No data is shared between users

## Troubleshooting

### Common Issues

1. **"PINECONE_API_KEY environment variable not set"**
   - Ensure you've created a `.env` file with your Pinecone API key

2. **"OPENAI_API_KEY environment variable not set"**
   - Ensure you've added your OpenAI API key to the `.env` file

3. **"Failed to create Pinecone index"**
   - Check your Pinecone account limits
   - Ensure you have sufficient quota for a new index

4. **"No relevant financial data found"**
   - Ensure you've uploaded financial documents with `store_in_vector_db=true`
   - Check that the user_id matches between upload and chat requests

### Health Checks

Monitor system health with:
```bash
curl -X GET "http://localhost:8000/health/chatbot"
```

This will test connectivity to Pinecone and OpenAI services.

## Advanced Configuration

You can customize the following settings in the code:

- **Index Name**: Default is `financial-documents`
- **Embedding Model**: Default is `text-embedding-3-small` (OpenAI)
- **Chat Model**: Default is `gpt-4o` (OpenAI)
- **Vector Dimensions**: 1536 (matches text-embedding-3-small embeddings)
- **Search Results**: Default top_k is 5-8 depending on the operation

## Next Steps

1. Set up your environment variables
2. Start the server: `python main.py`
3. Upload a financial document
4. Try chatting with your data!

For support or questions, please refer to the API documentation at `http://localhost:8000/docs` when the server is running.
