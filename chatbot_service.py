import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
import ollama
from dotenv import load_dotenv
import os
from pinecone_manager import get_pinecone_manager

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialChatbot:
    """
    AI-powered chatbot for querying financial documents and data
    """
    
    def __init__(self):
        """Initialize the chatbot with OpenAI client and Pinecone manager"""
        try:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.pinecone_manager = get_pinecone_manager()
            
            logger.info("FinancialChatbot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FinancialChatbot: {str(e)}")
            raise
    
    def create_context_from_results(self, search_results: List[Dict]) -> str:
        """
        Create context string from Pinecone search results
        """
        try:
            if not search_results:
                return "No relevant financial data found for this query."
            
            context_parts = []
            seen_docs = set()
            
            for result in search_results:
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "Unknown Document")
                chunk_type = metadata.get("chunk_type", "general")
                text = metadata.get("text", "")
                score = result.get("score", 0)
                
                # Add document info if not seen before or if it's highly relevant
                doc_key = f"{filename}_{chunk_type}"
                if doc_key not in seen_docs or score > 0.8:
                    context_parts.append(f"\n--- {filename} ({chunk_type.replace('_', ' ').title()}) [Relevance: {score:.3f}] ---")
                    
                    # Try to format JSON data more readably
                    formatted_text = self.format_financial_data(text)
                    context_parts.append(formatted_text)
                    seen_docs.add(doc_key)
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to create context from results: {str(e)}")
            return "Error processing financial data context."
    
    def format_financial_data(self, text: str) -> str:
        """
        Format financial data text for better readability
        """
        try:
            # If the text contains JSON-like structures, try to make them more readable
            import re
            
            # Replace JSON formatting with more readable format
            text = re.sub(r'{\s*"([^"]+)":\s*([^,}\n]+),?\s*', r'\1: \2\n', text)
            text = re.sub(r'{\s*\n', '', text)
            text = re.sub(r'\s*}', '', text)
            
            # Clean up extra newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text.strip()
            
        except Exception as e:
            logger.debug(f"Failed to format financial data: {e}")
            return text
    
    def enhance_financial_query(self, user_message: str) -> str:
        """
        Enhance user query to improve financial data retrieval
        """
        # Common financial terms and their variations
        financial_keywords = {
            "gross profit margin": ["gross profit margin", "gross margin", "profitability ratios"],
            "profit margin": ["profit margin", "net profit margin", "operating profit margin", "profitability"],
            "revenue": ["revenue", "total revenue", "sales", "income"],
            "expenses": ["expenses", "costs", "expenditures", "operating expenses"],
            "cash flow": ["cash flow", "operating cash flow", "free cash flow"],
            "balance sheet": ["balance sheet", "assets", "liabilities", "equity"],
            "ratios": ["ratios", "financial ratios", "kpis", "metrics"],
            "profit": ["profit", "net income", "earnings"],
            "debt": ["debt", "leverage", "liabilities"]
        }
        
        enhanced_terms = []
        user_lower = user_message.lower()
        
        # Add original query
        enhanced_terms.append(user_message)
        
        # Find matching financial concepts and add related terms
        for concept, variations in financial_keywords.items():
            if any(term in user_lower for term in variations):
                enhanced_terms.extend(variations)
                break
        
        # Create enhanced query focusing on the most relevant terms
        if len(enhanced_terms) > 1:
            # Prioritize the most specific financial terms
            enhanced_query = f"{user_message} {' '.join(enhanced_terms[1:3])}"  # Original + top 2 related terms
        else:
            enhanced_query = user_message
            
        return enhanced_query

    def generate_system_prompt(self) -> str:
        """
        Generate system prompt for the financial chatbot
        """
        return """
You are an expert Financial AI Assistant specializing in financial analysis and business intelligence. You have access to comprehensive financial data from uploaded documents including:

- Profit & Loss statements
- Balance sheets  
- Cash flow statements
- Financial ratios and KPIs
- Strategic recommendations
- AI-powered insights and trend analysis

Your role is to:
1. Answer questions about financial performance, trends, and metrics
2. Provide actionable insights and recommendations
3. Explain financial concepts in clear, business-friendly language
4. Identify potential risks and opportunities
5. Compare financial performance across different periods or documents
6. Help users understand their financial position and make informed decisions

Guidelines:
- Always base your responses on the provided financial data context
- Be specific with numbers and percentages when available
- Explain the business implications of financial metrics
- Provide actionable recommendations when appropriate
- If information is not available in the context, clearly state that
- Use professional but accessible language
- Focus on key insights that drive business value

Remember: You are analyzing real financial data from the user's uploaded documents. Be accurate, insightful, and helpful in your responses.
"""
    
    def chat(self, 
             user_message: str, 
             user_id: Optional[str] = None,
             conversation_history: Optional[List[Dict]] = None,
             document_filter: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process user message and return chatbot response
        """
        try:
            # Enhance the query for better financial data retrieval
            enhanced_query = self.enhance_financial_query(user_message)
            logger.info(f"Enhanced query: '{enhanced_query}' from original: '{user_message}'")
            
            # Search for relevant financial data using Ollama embeddings
            search_results = self.pinecone_manager.query_financial_data(
                query=enhanced_query,
                user_id=user_id,
                top_k=10,  # Get more results for comprehensive context
                filter_dict=document_filter
            )
            
            # If no results found with enhanced query, try with original query
            if not search_results:
                logger.warning(f"No results with enhanced query, trying original query: '{user_message}'")
                search_results = self.pinecone_manager.query_financial_data(
                    query=user_message,
                    user_id=user_id,
                    top_k=10,
                    filter_dict=document_filter
                )
            
            # If still no results and user_id was provided, try without user filter
            if not search_results and user_id:
                logger.warning(f"No results with user filter, trying without user_id filter")
                search_results = self.pinecone_manager.query_financial_data(
                    query=enhanced_query,
                    user_id=None,  # Remove user filter
                    top_k=10,
                    filter_dict=document_filter
                )
            
            # Create context from search results
            context = self.create_context_from_results(search_results)
            
            # Prepare conversation messages
            messages = [{"role": "system", "content": self.generate_system_prompt()}]
            
            # Add conversation history if provided (validate format)
            if conversation_history:
                valid_history = []
                for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                    if isinstance(msg, dict) and "content" in msg:
                        # Handle both "role" and "sender" formats
                        role = None
                        if "role" in msg:
                            role = msg["role"]
                        elif "sender" in msg:
                            # Convert frontend format to OpenAI format
                            if msg["sender"] == "user":
                                role = "user"
                            elif msg["sender"] in ["bot", "assistant"]:
                                role = "assistant"
                        
                        # Ensure role is valid
                        if role in ["user", "assistant", "system"]:
                            valid_history.append({
                                "role": role,
                                "content": str(msg["content"])
                            })
                        else:
                            logger.warning(f"Invalid message role/sender: {msg.get('role', msg.get('sender'))}")
                    else:
                        logger.warning(f"Invalid message format in conversation history: {msg}")
                
                messages.extend(valid_history)
            
            # Add current context and user message
            context_message = f"""
Based on the following financial data context, please answer the user's question:

FINANCIAL DATA CONTEXT:
{context}

USER QUESTION: {user_message}
"""
            
            messages.append({"role": "user", "content": context_message})
            
            # Debug: Log message structure
            logger.info(f"Sending {len(messages)} messages to OpenAI")
            for i, msg in enumerate(messages):
                logger.debug(f"Message {i}: role={msg.get('role')}, content_length={len(str(msg.get('content', '')))}")
            
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,  # Lower temperature for more factual responses
                max_tokens=1500
            )
            
            assistant_response = response.choices[0].message.content
            
            # Prepare response data
            response_data = {
                "response": assistant_response,
                "sources_used": len(search_results),
                "relevant_documents": list(set([
                    result["metadata"].get("filename", "Unknown") 
                    for result in search_results
                ])),
                "context_chunks": [
                    {
                        "filename": result["metadata"].get("filename"),
                        "chunk_type": result["metadata"].get("chunk_type"),
                        "relevance_score": round(result["score"], 3)
                    }
                    for result in search_results[:5]  # Top 5 most relevant
                ]
            }
            
            logger.info(f"Generated chatbot response for user {user_id}, used {len(search_results)} sources")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to generate chatbot response: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error while processing your question. Please try again or rephrase your question.",
                "error": str(e),
                "sources_used": 0,
                "relevant_documents": [],
                "context_chunks": []
            }
    
# Document summary and question suggestions now handled by frontend PostgreSQL integration

# Global instance
financial_chatbot = None

def get_financial_chatbot() -> FinancialChatbot:
    """Get or create a global FinancialChatbot instance"""
    global financial_chatbot
    if financial_chatbot is None:
        financial_chatbot = FinancialChatbot()
    return financial_chatbot
