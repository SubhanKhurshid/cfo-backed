import pandas as pd
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize OpenAI client with Gemini API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

def read_excel_file(file_path):
    """Read and process the Excel file - simplified version"""
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None, None
        
        print(f"Reading file: {file_path}")
        
        # Read from Sheet1 (where the data is located)
        df = pd.read_excel(file_path, sheet_name='Sheet1', header=None)
        
        if df.empty:
            print("No data found in Sheet1")
            return None, None
        
        print(f"Data loaded successfully! Shape: {df.shape}")
        
        # Convert to string representation for LLM analysis
        excel_data = df.to_string(index=True, na_rep='', max_rows=None, max_cols=None)
        
        return excel_data, df
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None, None

def create_system_prompt():
    """Create comprehensive system prompt for financial analysis"""
    return """
You are an expert financial analyst. Analyze the provided Excel financial data and return a comprehensive analysis in JSON format.

The data appears to be a financial budget/report with monthly columns and various income/expense categories. Look for:
- Income categories (Consulting Income, Cleaning Income, etc.)
- Expense categories (Advertising, Cleaning Expenses, Rent, etc.)
- Monthly data across different time periods
- Totals in the rightmost column

CRITICAL: You must return ONLY valid JSON. No explanations, no markdown, no text before or after the JSON.

Return this EXACT JSON structure with actual data from the spreadsheet:
```
json
{
  "financial_summary": {
    "total_revenue": 0.00,
    "total_expense": 0.00,
    "net_profit": 0.00,
    "gross_profit": 0.00
  },
  "revenue_breakdown": {
    "consulting_income": 0.00,
    "cleaning_income": 0.00,
    "app_income": 0.00,
    "other_income": 0.00
  },
  "expense_breakdown": {
    "cost_of_goods_sold": 0.00,
    "advertising_promotion": 0.00,
    "cleaning_expenses": 0.00,
    "automobile_expense": 0.00,
    "rent_expense": 0.00,
    "insurance_expense": 0.00,
    "professional_fees": 0.00,
    "office_supplies": 0.00,
    "other_expenses": 0.00
  },
  "top_accounts": {
    "highest_revenue_source": {
      "account_name": "Account Name",
      "amount": 0.00
    },
    "highest_expense_category": {
      "account_name": "Account Name",
      "amount": 0.00
    }
  },
  "financial_ratios": {
    "gross_profit_margin": 0.00,
    "net_profit_margin": 0.00,
    "expense_ratio": 0.00
  },
  "monthly_analysis": {
    "average_monthly_revenue": 0.00,
    "average_monthly_expenses": 0.00,
    "trend": "stable"
  },
  "recommendations": [
    {
      "category": "cost_reduction",
      "recommendation": "Recommendation text here",
      "priority": "medium"
    }
  ],
  "anomalies": [
    {
      "description": "Anomaly description",
      "impact": "medium"
    }
  ]
}
```        
Extract actual numbers from the data and replace 0.00 with real values. Use only standard JSON - no trailing commas, proper quotes, valid syntax.
"""

def analyze_financial_data(excel_data):
    """Send data to LLM for analysis"""
    try:
        system_prompt = create_system_prompt()
        
        user_message = f"""
Analyze this Excel financial data and return JSON analysis:

{excel_data}

IMPORTANT: Return ONLY valid JSON. No explanations, no markdown, no additional text. Just the JSON object.
"""

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0
        )
        
        analysis_result = response.choices[0].message.content.strip()
        print("Raw AI response preview:", analysis_result)
        
        # Clean the response
        analysis_result = analysis_result.strip()
        
        # Remove markdown code blocks if present
        if analysis_result.startswith("```json"):
            analysis_result = analysis_result[7:]
        if analysis_result.startswith("```"):
            analysis_result = analysis_result[3:]
        if analysis_result.endswith("```"):
            analysis_result = analysis_result[:-3]
        
        analysis_result = analysis_result.strip()
        
        # Parse JSON response
        try:
            return json.loads(analysis_result)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Problematic JSON around character {e.pos}:")
            start = max(0, e.pos - 50)
            end = min(len(analysis_result), e.pos + 50)
            print(analysis_result[start:end])
            
            # Try to find and extract JSON object
            import re
            json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_result, re.DOTALL)
            
            for match in json_matches:
                try:
                    return json.loads(match)
                except:
                    continue
            
            # If all else fails, return error with raw response
            return {"error": "Failed to parse JSON response", "raw_response": analysis_result}
                
    except Exception as e:
        return {"error": f"API call failed: {str(e)}"}

def display_results(analysis_result):
    """Display analysis results in a formatted way"""
    if "error" in analysis_result:
        print(f" Error: {analysis_result['error']}")
        return
    
    print("Analysis completed successfully!")
    print("=" * 60)
    
    # Financial Summary
    if "financial_summary" in analysis_result:
        summary = analysis_result["financial_summary"]
        print("FINANCIAL SUMMARY")
        print(f"   Total Revenue:    ${summary.get('total_revenue', 0):,.2f}")
        print(f"   Total Expenses:   ${summary.get('total_expense', 0):,.2f}")
        print(f"   Gross Profit:     ${summary.get('gross_profit', 0):,.2f}")
        print(f"   Net Profit:       ${summary.get('net_profit', 0):,.2f}")
        print()
    
    # Top Accounts
    if "top_accounts" in analysis_result:
        top = analysis_result["top_accounts"]
        print("TOP ACCOUNTS")
        if "highest_revenue_source" in top:
            rev = top["highest_revenue_source"]
            print(f"   Highest Revenue: {rev.get('account_name', 'N/A')} (${rev.get('amount', 0):,.2f})")
        if "highest_expense_category" in top:
            exp = top["highest_expense_category"]
            print(f"   Highest Expense: {exp.get('account_name', 'N/A')} (${exp.get('amount', 0):,.2f})")
        print()
    
    # Financial Ratios
    if "financial_ratios" in analysis_result:
        ratios = analysis_result["financial_ratios"]
        print("FINANCIAL RATIOS")
        print(f"   Gross Profit Margin: {ratios.get('gross_profit_margin', 0):.1f}%")
        print(f"   Net Profit Margin:   {ratios.get('net_profit_margin', 0):.1f}%")
        print(f"   Expense Ratio:       {ratios.get('expense_ratio', 0):.1f}%")
        print()
    
    # Recommendations
    if "recommendations" in analysis_result and analysis_result["recommendations"]:
        print("KEY RECOMMENDATIONS")
        for i, rec in enumerate(analysis_result["recommendations"][:3], 1):
            priority = rec.get('priority', 'medium').upper()
            print(f"   {i}. [{priority}] {rec.get('recommendation', 'N/A')}")
        print()
    
    # Anomalies
    if "anomalies" in analysis_result and analysis_result["anomalies"]:
        print(" ANOMALIES DETECTED")
        for i, anomaly in enumerate(analysis_result["anomalies"][:3], 1):
            impact = anomaly.get('impact', 'medium').upper()
            print(f"   {i}. [{impact}] {anomaly.get('description', 'N/A')}")

def save_analysis_to_file(analysis, output_file="financial_analysis.json"):
    """Save analysis results to JSON file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"Full analysis saved to {output_file}")
    except Exception as e:
        print(f"Error saving analysis: {e}")

def main():
    """Main function"""
    file_path = "data/Budget_March.xlsx"
    
    # Read Excel file
    print("Reading Excel file...")
    excel_data, df = read_excel_file(file_path)
    
    if excel_data is None:
        print("Failed to read Excel file")
        return None
    
    # Analyze with LLM
    print("Analyzing data with AI...")
    analysis_result = analyze_financial_data(excel_data)
    
    # Display results
    display_results(analysis_result)
    
    # Save to file
    if "error" not in analysis_result:
        save_analysis_to_file(analysis_result)
    
    return analysis_result

if __name__ == "__main__":
    result = main()