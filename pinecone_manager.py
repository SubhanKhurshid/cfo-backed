import os
import json
import uuid
import requests
import time
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import ollama
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeManager:
    """
    Manages Pinecone vector database operations for financial data storage and retrieval
    """
    
    def __init__(self):
        """Initialize Pinecone client and Ollama for embeddings"""
        try:
            # Initialize Pinecone
            self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if not self.pinecone_api_key:
                raise ValueError("PINECONE_API_KEY environment variable not set")
            
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            
            # Initialize OpenAI for chat (still needed for analysis)
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            
            # Ollama configuration for embeddings
            self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self.embedding_model = "nomic-embed-text:latest"
            
            # Test Ollama connection
            self._test_ollama_connection()
            
            # Pinecone index configuration
            self.index_name = "financial-documents"
            self.dimension = 768  # nomic-embed-text embedding dimension
            self.metric = "cosine"
            
            # Initialize or connect to index
            self._setup_index()
            
            logger.info("PineconeManager initialized successfully with Ollama embeddings")
            
        except Exception as e:
            logger.error(f"Failed to initialize PineconeManager: {str(e)}")
            raise
    
    def _test_ollama_connection(self):
        """Test connection to Ollama server and verify model availability"""
        try:
            # Test if Ollama server is running
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                raise Exception(f"Ollama server not accessible at {self.ollama_base_url}")
            
            # Check if the embedding model is available
            models = response.json()
            model_names = [model.get('name', '') for model in models.get('models', [])]
            
            if self.embedding_model not in model_names:
                logger.warning(f"Model {self.embedding_model} not found. Attempting to pull...")
                # Try to pull the model
                try:
                    ollama.pull(self.embedding_model)
                    logger.info(f"Successfully pulled model {self.embedding_model}")
                except Exception as pull_error:
                    raise Exception(f"Model {self.embedding_model} not available and failed to pull: {str(pull_error)}")
            
            logger.info(f"Ollama connection verified. Model {self.embedding_model} is available.")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Ollama server at {self.ollama_base_url}: {str(e)}")
        except Exception as e:
            raise Exception(f"Ollama connection test failed: {str(e)}")
    
    def _setup_index(self):
        """Setup Pinecone index for financial documents"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name not in index_names:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                
                # Create index with serverless spec
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                logger.info(f"Index {self.index_name} created successfully")
            else:
                logger.info(f"Index {self.index_name} already exists")
            
            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Connected to index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup Pinecone index: {str(e)}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text using Ollama nomic-embed-text model"""
        try:
            # Use Ollama to generate embeddings
            response = ollama.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            
            # Extract embedding from response
            if 'embedding' in response:
                embedding = response['embedding']
                logger.debug(f"Generated embedding of dimension {len(embedding)} for text length {len(text)}")
                return embedding
            else:
                raise Exception("No embedding found in Ollama response")
                
        except Exception as e:
            logger.error(f"Failed to generate embedding with Ollama: {str(e)}")
            # Fallback to OpenAI if Ollama fails
            logger.warning("Falling back to OpenAI embeddings")
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except Exception as openai_error:
                logger.error(f"OpenAI fallback also failed: {str(openai_error)}")
                raise Exception(f"Both Ollama and OpenAI embedding generation failed. Ollama: {str(e)}, OpenAI: {str(openai_error)}")
    
    def prepare_financial_data_for_storage(self, 
                                         financial_analysis: Dict[Any, Any], 
                                         file_info: Dict[str, Any],
                                         user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Prepare financial analysis data for vector storage
        Creates multiple chunks for different aspects of the financial data
        """
        try:
            chunks = []
            doc_id = str(uuid.uuid4())
            timestamp = str(int(time.time() * 1000))  # Current timestamp in milliseconds
            
            # Extract key information
            filename = file_info.get("filename", "unknown")
            file_type = file_info.get("file_type", "unknown")
            
            # 1. Executive Summary Chunk
            if "executive_summary" in financial_analysis:
                exec_summary = financial_analysis["executive_summary"]
                summary_text = f"""
                Financial Document: {filename}
                Business Health Score: {exec_summary.get('business_health_score', 'N/A')}
                Financial Strength: {exec_summary.get('financial_strength', 'N/A')}
                Key Performance Indicators: {json.dumps(exec_summary.get('key_performance_indicators', {}), indent=2)}
                Critical Alerts: {'; '.join(exec_summary.get('critical_alerts', []))}
                """
                
                chunks.append({
                    "id": f"{doc_id}_executive_summary",
                    "text": summary_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "executive_summary",
                        "timestamp": timestamp
                    }
                })
            
            # 2. Profit & Loss Chunk
            if "profit_and_loss" in financial_analysis:
                pl_data = financial_analysis["profit_and_loss"]
                pl_text = f"""
                Profit & Loss Statement for {filename}:
                Revenue Analysis: Total Revenue: ${pl_data.get('revenue_analysis', {}).get('total_revenue', 0):,.2f}
                Revenue Streams: {json.dumps(pl_data.get('revenue_analysis', {}).get('revenue_streams', {}), indent=2)}
                Cost Structure: Total Expenses: ${pl_data.get('cost_structure', {}).get('total_expenses', 0):,.2f}
                Cost Categories: {json.dumps(pl_data.get('cost_structure', {}).get('cost_categories', {}), indent=2)}
                Profitability: Gross Profit: ${pl_data.get('profitability_metrics', {}).get('gross_profit', 0):,.2f}
                Net Income: ${pl_data.get('profitability_metrics', {}).get('net_income', 0):,.2f}
                Margins: {json.dumps(pl_data.get('profitability_metrics', {}).get('margins', {}), indent=2)}
                """
                
                chunks.append({
                    "id": f"{doc_id}_profit_loss",
                    "text": pl_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "profit_and_loss",
                        "timestamp": timestamp
                    }
                })
            
            # 3. Balance Sheet Chunk
            if "balance_sheet" in financial_analysis:
                bs_data = financial_analysis["balance_sheet"]
                bs_text = f"""
                Balance Sheet for {filename}:
                Assets: Total Assets: ${bs_data.get('assets', {}).get('total_assets', 0):,.2f}
                Current Assets: {json.dumps(bs_data.get('assets', {}).get('current_assets', {}), indent=2)}
                Non-Current Assets: {json.dumps(bs_data.get('assets', {}).get('non_current_assets', {}), indent=2)}
                Liabilities: Total Liabilities: ${bs_data.get('liabilities', {}).get('total_liabilities', 0):,.2f}
                Current Liabilities: {json.dumps(bs_data.get('liabilities', {}).get('current_liabilities', {}), indent=2)}
                Long-term Liabilities: {json.dumps(bs_data.get('liabilities', {}).get('long_term_liabilities', {}), indent=2)}
                Equity: Total Equity: ${bs_data.get('equity', {}).get('total_equity', 0):,.2f}
                """
                
                chunks.append({
                    "id": f"{doc_id}_balance_sheet",
                    "text": bs_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "balance_sheet",
                        "timestamp": timestamp
                    }
                })
            
            # 4. Cash Flow Chunk
            if "cash_flow_analysis" in financial_analysis:
                cf_data = financial_analysis["cash_flow_analysis"]
                cf_text = f"""
                Cash Flow Analysis for {filename}:
                Operating Activities: Net Cash from Operations: ${cf_data.get('operating_activities', {}).get('net_cash_from_operations', 0):,.2f}
                Investing Activities: Net Cash from Investing: ${cf_data.get('investing_activities', {}).get('net_investing_cash_flow', 0):,.2f}
                Financing Activities: Net Cash from Financing: ${cf_data.get('financing_activities', {}).get('net_financing_cash_flow', 0):,.2f}
                Cash Position: Beginning Cash: ${cf_data.get('cash_position', {}).get('beginning_cash', 0):,.2f}
                Ending Cash: ${cf_data.get('cash_position', {}).get('ending_cash', 0):,.2f}
                Free Cash Flow: ${cf_data.get('cash_position', {}).get('free_cash_flow', 0):,.2f}
                """
                
                chunks.append({
                    "id": f"{doc_id}_cash_flow",
                    "text": cf_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "cash_flow",
                        "timestamp": timestamp
                    }
                })
            
            # 5. Financial Ratios & KPIs Chunk
            if "financial_ratios" in financial_analysis:
                ratios_data = financial_analysis["financial_ratios"]
                ratios_text = f"""
                Financial Ratios and KPIs for {filename}:
                Profitability Ratios: {json.dumps(ratios_data.get('profitability_ratios', {}), indent=2)}
                Liquidity Ratios: {json.dumps(ratios_data.get('liquidity_ratios', {}), indent=2)}
                Efficiency Ratios: {json.dumps(ratios_data.get('efficiency_ratios', {}), indent=2)}
                Leverage Ratios: {json.dumps(ratios_data.get('leverage_ratios', {}), indent=2)}
                """
                
                chunks.append({
                    "id": f"{doc_id}_financial_ratios",
                    "text": ratios_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "financial_ratios",
                        "timestamp": timestamp
                    }
                })
            
            # 6. Strategic Recommendations Chunk
            if "strategic_recommendations" in financial_analysis:
                rec_data = financial_analysis["strategic_recommendations"]
                rec_text = f"""
                Strategic Recommendations for {filename}:
                Immediate Actions (0-30 days): {json.dumps(rec_data.get('immediate_actions_0_30_days', []), indent=2)}
                Short-term Improvements (1-6 months): {json.dumps(rec_data.get('short_term_improvements_1_6_months', []), indent=2)}
                Long-term Strategic Initiatives (6-24 months): {json.dumps(rec_data.get('long_term_strategic_initiatives_6_24_months', []), indent=2)}
                Growth Opportunities: {json.dumps(rec_data.get('growth_opportunities', []), indent=2)}
                Risk Mitigation Strategies: {json.dumps(rec_data.get('risk_mitigation_strategies', []), indent=2)}
                """
                
                chunks.append({
                    "id": f"{doc_id}_strategic_recommendations",
                    "text": rec_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "strategic_recommendations",
                        "timestamp": timestamp
                    }
                })
            
            # 7. AI Insights Chunk
            if "ai_powered_insights" in financial_analysis:
                ai_data = financial_analysis["ai_powered_insights"]
                ai_text = f"""
                AI-Powered Insights for {filename}:
                Trend Analysis: {json.dumps(ai_data.get('trend_analysis', []), indent=2)}
                Anomaly Detection: {json.dumps(ai_data.get('anomaly_detection', []), indent=2)}
                Pattern Recognition: {json.dumps(ai_data.get('pattern_recognition', []), indent=2)}
                Predictive Alerts: {json.dumps(ai_data.get('predictive_alerts', []), indent=2)}
                Performance Benchmarking: {json.dumps(ai_data.get('performance_benchmarking', {}), indent=2)}
                """
                
                chunks.append({
                    "id": f"{doc_id}_ai_insights",
                    "text": ai_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "ai_insights",
                        "timestamp": timestamp
                    }
                })
            
            # 8. Key Insights Summary Chunk
            if "key_insights_summary" in financial_analysis:
                insights_list = financial_analysis["key_insights_summary"]
                insights_text = f"""
                Key Insights Summary for {filename}:
                {chr(10).join(f"• {insight}" for insight in insights_list)}
                """
                
                chunks.append({
                    "id": f"{doc_id}_key_insights",
                    "text": insights_text.strip(),
                    "metadata": {
                        "user_id": user_id or "anonymous",
                        "document_id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_type": "key_insights",
                        "timestamp": timestamp
                    }
                })
            
            logger.info(f"Prepared {len(chunks)} chunks for document {filename}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to prepare financial data for storage: {str(e)}")
            raise
    
    def store_financial_data(self, 
                           financial_analysis: Dict[Any, Any], 
                           file_info: Dict[str, Any],
                           user_id: Optional[str] = None) -> str:
        """
        Store financial analysis data in Pinecone
        Returns the document ID for future reference
        """
        try:
            # Prepare data chunks
            chunks = self.prepare_financial_data_for_storage(financial_analysis, file_info, user_id)
            
            if not chunks:
                raise ValueError("No chunks prepared for storage")
            
            # Generate embeddings and prepare vectors
            vectors = []
            for chunk in chunks:
                embedding = self.generate_embedding(chunk["text"])
                vectors.append({
                    "id": chunk["id"],
                    "values": embedding,
                    "metadata": {
                        **chunk["metadata"],
                        "text": chunk["text"][:1000]  # Store first 1000 chars in metadata for quick access
                    }
                })
            
            # Upsert vectors to Pinecone
            self.index.upsert(vectors=vectors)
            
            doc_id = chunks[0]["metadata"]["document_id"]
            logger.info(f"Successfully stored {len(vectors)} vectors for document {file_info.get('filename')} with doc_id: {doc_id}")
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to store financial data: {str(e)}")
            raise
    
    def query_financial_data(self, 
                           query: str, 
                           user_id: Optional[str] = None,
                           top_k: int = 5,
                           filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Query financial data from Pinecone using semantic search
        """
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)
            
            # Prepare filter
            filter_conditions = {}
            if user_id:
                filter_conditions["user_id"] = user_id
            if filter_dict:
                filter_conditions.update(filter_dict)
            
            # Query Pinecone
            query_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_conditions if filter_conditions else None
            )
            
            # Process results
            results = []
            for match in query_results.matches:
                results.append({
                    "score": match.score,
                    "metadata": match.metadata,
                    "id": match.id
                })
            
            logger.info(f"Found {len(results)} matches for query: {query[:100]}...")
            
            # Debug: Log top results with scores
            for i, result in enumerate(results[:3]):
                metadata = result.get("metadata", {})
                logger.info(f"Result {i+1}: score={result['score']:.4f}, filename={metadata.get('filename')}, chunk_type={metadata.get('chunk_type')}")
            
            # If no results found, log more debugging info
            if not results:
                logger.warning(f"No results found for query: '{query}'. Filter: {filter_conditions}")
                # Try to get total index stats
                try:
                    stats = self.index.describe_index_stats()
                    logger.info(f"Index stats: {stats}")
                except Exception as e:
                    logger.error(f"Failed to get index stats: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query financial data: {str(e)}")
            raise
    
    def get_user_documents(self, user_id: str) -> List[Dict]:
        """
        Get all documents for a specific user
        """
        try:
            # Query with user filter to get all chunks for this user
            query_results = self.index.query(
                vector=[0.0] * self.dimension,  # Dummy vector since we're filtering by metadata
                top_k=1000,  # Large number to get all docs
                include_metadata=True,
                filter={"user_id": user_id}
            )
            
            # Group by document_id to get unique documents
            documents = {}
            for match in query_results.matches:
                doc_id = match.metadata.get("document_id")
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": match.metadata.get("filename"),
                        "file_type": match.metadata.get("file_type"),
                        "timestamp": match.metadata.get("timestamp"),
                        "chunks": 0
                    }
                documents[doc_id]["chunks"] += 1
            
            return list(documents.values())
            
        except Exception as e:
            logger.error(f"Failed to get user documents: {str(e)}")
            raise
    
    def delete_document(self, document_id: str, user_id: str) -> bool:
        """
        Delete all chunks of a document for a user
        """
        try:
            # Get all chunk IDs for this document and user
            query_results = self.index.query(
                vector=[0.0] * self.dimension,
                top_k=1000,
                include_metadata=True,
                filter={"document_id": document_id, "user_id": user_id}
            )
            
            # Extract chunk IDs
            chunk_ids = [match.id for match in query_results.matches]
            
            if chunk_ids:
                # Delete all chunks
                self.index.delete(ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} chunks for document {document_id}")
                return True
            else:
                logger.warning(f"No chunks found for document {document_id} and user {user_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise

# Global instance
pinecone_manager = None

def get_pinecone_manager() -> PineconeManager:
    """Get or create a global PineconeManager instance"""
    global pinecone_manager
    if pinecone_manager is None:
        pinecone_manager = PineconeManager()
    return pinecone_manager
