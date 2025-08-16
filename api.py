import pandas as pd
import json
from openai import OpenAI
from dotenv import load_dotenv
import os
import PyPDF2
import pdfplumber

# Load environment variables
load_dotenv()

# Initialize OpenAI client with Gemini API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(
    
    api_key=OPENAI_API_KEY
)

def read_excel_file(file_path):
    """Read and process Excel files (XLSX and XLS) with improved sheet detection"""
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None, None
        
        print(f"Reading Excel file: {file_path}")
        
        # First, try to get all sheet names
        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            print(f"Available sheets: {sheet_names}")
        except Exception as e:
            print(f"Error reading sheet names: {e}")
            return None, None
        
        # Try different approaches to read the data
        df = None
        
        # Approach 1: Try reading the first sheet with default settings
        try:
            df = pd.read_excel(file_path, sheet_name=0, header=None)
            print(f"Successfully read first sheet: {sheet_names[0] if sheet_names else 'Sheet1'}")
        except Exception as e:
            print(f"Error reading first sheet: {e}")
        
        # Approach 2: If first approach failed, try reading with different parameters
        if df is None or df.empty:
            try:
                # Try reading with header detection
                df = pd.read_excel(file_path, sheet_name=0, header=0)
                print(f"Successfully read with header detection")
            except Exception as e:
                print(f"Error reading with header detection: {e}")
        
        # Approach 3: Try reading specific sheet names if available
        if df is None or df.empty:
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                    if not df.empty:
                        print(f"Successfully read sheet: {sheet_name}")
                        break
                except Exception as e:
                    print(f"Error reading sheet {sheet_name}: {e}")
                    continue
        
        # Approach 4: Try reading all sheets and combine
        if df is None or df.empty:
            try:
                all_sheets = pd.read_excel(file_path, sheet_name=None, header=None)
                if all_sheets:
                    # Combine all sheets
                    combined_data = []
                    for sheet_name, sheet_df in all_sheets.items():
                        if not sheet_df.empty:
                            combined_data.append(f"\n--- Sheet: {sheet_name} ---\n")
                            combined_data.append(sheet_df.to_string(index=True, na_rep=''))
                    
                    if combined_data:
                        excel_data = "\n".join(combined_data)
                        print(f"Successfully read and combined {len(all_sheets)} sheets")
                        return excel_data, None
            except Exception as e:
                print(f"Error reading all sheets: {e}")
        
        if df is None or df.empty:
            print("No data found in any sheet")
            return None, None
        
        print(f"Excel data loaded successfully! Shape: {df.shape}")
        
        # Convert to string representation for LLM analysis
        excel_data = df.to_string(index=True, na_rep='', max_rows=None, max_cols=None)
        
        return excel_data, df
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None, None

def read_pdf_file(file_path):
    """Read and process PDF financial documents"""
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        print(f"Reading PDF file: {file_path}")
        
        # Method 1: Try with pdfplumber (better for tables and structured data)
        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                tables_data = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    print(f"Processing page {page_num}...")
                    
                    # Extract text from page
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
                    
                    # Extract tables from page
                    tables = page.extract_tables()
                    if tables:
                        for table_num, table in enumerate(tables, 1):
                            tables_data.append({
                                "page": page_num,
                                "table": table_num,
                                "data": table
                            })
                            
                            # Convert table to string format
                            table_str = f"\n--- Page {page_num} Table {table_num} ---\n"
                            for row in table:
                                if row:  # Skip empty rows
                                    row_str = " | ".join([str(cell) if cell else "" for cell in row])
                                    table_str += row_str + "\n"
                            full_text += table_str
                
                if full_text.strip():
                    print(f"PDF data extracted successfully! Pages: {len(pdf.pages)}, Tables: {len(tables_data)}")
                    return full_text.strip()
                else:
                    print("No text content found in PDF")
                    return None
                    
        except Exception as e:
            print(f"Error with pdfplumber: {e}")
            # Fallback to PyPDF2
            print("Trying fallback method with PyPDF2...")
            
        # Method 2: Fallback with PyPDF2 (simpler text extraction)
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                full_text = ""
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
                
                if full_text.strip():
                    print(f"PDF data extracted successfully with PyPDF2! Pages: {len(pdf_reader.pages)}")
                    return full_text.strip()
                else:
                    print("No text content found in PDF")
                    return None
                    
        except Exception as e:
            print(f"Error with PyPDF2: {e}")
            return None
            
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None

def read_csv_file(file_path):
    """Read and process CSV financial documents"""
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        print(f"Reading CSV file: {file_path}")
        
        # Try different encodings to handle various CSV files
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"Successfully read CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error with {encoding} encoding: {e}")
                continue
        
        if df is None:
            print("Failed to read CSV with any encoding")
            return None
        
        if df.empty:
            print("No data found in CSV")
            return None
        
        print(f"CSV data loaded successfully! Shape: {df.shape}")
        
        # Convert to string representation for LLM analysis
        csv_data = df.to_string(index=True, na_rep='', max_rows=None, max_cols=None)
        
        return csv_data
        
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def detect_file_type(file_path):
    """Detect file type based on extension"""
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension in ['.xlsx', '.xls']:
        return 'excel'
    elif file_extension == '.pdf':
        return 'pdf'
    elif file_extension == '.csv':
        return 'csv'
    else:
        return 'unknown'

def read_financial_file(file_path):
    """Universal file reader for financial documents (Excel, PDF, or CSV)"""
    file_type = detect_file_type(file_path)
    
    if file_type == 'excel':
        excel_data, df = read_excel_file(file_path)
        return excel_data, 'excel'
    elif file_type == 'pdf':
        pdf_data = read_pdf_file(file_path)
        return pdf_data, 'pdf'
    elif file_type == 'csv':
        csv_data = read_csv_file(file_path)
        return csv_data, 'csv'
    else:
        print(f"Unsupported file type: {file_path}")
        return None, 'unknown'

def create_system_prompt():
    """Create comprehensive system prompt for advanced financial analysis and strategic guidance"""
    return """
You are an elite CFO and strategic financial advisor with 20+ years of experience across multiple industries. You specialize in transforming raw financial data into actionable business intelligence that drives profitable growth and operational excellence.

MISSION: Analyze financial documents comprehensively and provide executive-level insights that empower business owners to make data-driven decisions, optimize performance, and navigate financial challenges with confidence.

CRITICAL: You MUST return ALL sections below in a complete, professional analysis. Never skip sections - provide comprehensive coverage even if data is limited.

CORE ANALYSIS FRAMEWORK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. FINANCIAL STATEMENTS GENERATION
   - Profit & Loss Statement (Income Statement)
   - Balance Sheet (Statement of Financial Position)  
   - Cash Flow Statement (Operating, Investing, Financing Activities)
   - Statement of Equity Changes

2. AGING ANALYSIS & WORKING CAPITAL MANAGEMENT
   - Accounts Receivable Aging (0-30, 31-60, 61-90, 90+ days)
   - Accounts Payable Aging with payment optimization
   - Working Capital Cycle Analysis
   - Cash Conversion Cycle Optimization

3. ADVANCED FINANCIAL RATIOS & KPIs
   - Profitability Ratios (Gross, Operating, Net, EBITDA margins)
   - Liquidity Ratios (Current, Quick, Cash ratios)
   - Efficiency Ratios (Asset turnover, Inventory turnover, AR/AP days)
   - Leverage Ratios (Debt-to-equity, Interest coverage, Debt service)
   - Return Metrics (ROE, ROA, ROIC)

4. WHAT-IF SCENARIO MODELING & STRESS TESTING
   - Revenue Impact Scenarios: +/-10%, +/-20%, +/-30%
   - Cost Structure Optimization: Fixed vs Variable cost analysis
   - Cash Flow Stress Testing under various scenarios
   - Break-even Analysis and Margin of Safety
   - Sensitivity Analysis for key business drivers

5. AI-POWERED PREDICTIVE INSIGHTS
   - Trend Analysis with statistical confidence levels
   - Anomaly Detection using advanced pattern recognition
   - Seasonal Pattern Identification and forecasting
   - Early Warning Systems for financial distress
   - Performance Benchmarking against industry standards

6. STRATEGIC RECOMMENDATIONS & ACTION PLANS
   - Immediate Actions (0-30 days)
   - Short-term Improvements (1-6 months)
   - Long-term Strategic Initiatives (6-24 months)
   - Risk Mitigation Strategies
   - Growth Opportunity Identification

ENHANCED DATA PROCESSING CAPABILITIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACCOUNT CLASSIFICATION INTELLIGENCE:
- Revenue Recognition: Service income, Product sales, Recurring revenue, One-time income
- Cost Structure Analysis: Direct costs, Indirect costs, Fixed vs Variable expenses
- Asset Categorization: Current/Non-current, Productive/Non-productive assets
- Liability Management: Current obligations, Long-term debt, Contingent liabilities
- Equity Structure: Owner investments, Retained earnings, Distribution analysis

ADVANCED KPI CALCULATIONS:
- EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization
- Free Cash Flow = Operating Cash Flow - Capital Expenditures
- Days Sales Outstanding (DSO) = (Accounts Receivable / Revenue) × 365
- Days Payable Outstanding (DPO) = (Accounts Payable / COGS) × 365
- Cash Conversion Cycle = DSO + DIO - DPO
- Return on Invested Capital (ROIC) = NOPAT / Invested Capital
- Economic Value Added (EVA) = NOPAT - (Capital × WACC)

CRITICAL: You must return ONLY valid JSON. No explanations, markdown, or additional text.

Return this COMPREHENSIVE JSON structure with real data analysis:
```
json
{
  "executive_summary": {
    "business_health_score": 0,
    "financial_strength": "strong|moderate|weak",
    "key_performance_indicators": {
      "revenue_trend": "increasing|stable|declining",
      "profitability_trend": "improving|stable|deteriorating",
      "cash_position": "strong|adequate|concerning",
      "operational_efficiency": "excellent|good|needs_improvement"
    },
    "critical_alerts": [
      "Immediate attention required items"
    ]
  },
  
  "profit_and_loss": {
    "revenue_analysis": {
      "total_revenue": 0.00,
      "revenue_streams": {
        "primary_revenue": 0.00,
        "secondary_revenue": 0.00,
        "recurring_revenue": 0.00,
        "one_time_revenue": 0.00
      },
      "revenue_quality_metrics": {
        "recurring_percentage": 0.00,
        "customer_concentration_risk": "low|medium|high",
        "revenue_predictability": 0.00
      }
    },
    "cost_structure": {
      "total_expenses": 0.00,
      "cost_categories": {
        "direct_costs": 0.00,
        "operating_expenses": 0.00,
        "administrative_costs": 0.00,
        "financing_costs": 0.00
      },
      "cost_behavior": {
        "fixed_costs": 0.00,
        "variable_costs": 0.00,
        "semi_variable_costs": 0.00
      }
    },
    "profitability_metrics": {
      "gross_profit": 0.00,
      "operating_profit": 0.00,
      "ebitda": 0.00,
      "net_income": 0.00,
      "margins": {
        "gross_margin": 0.00,
        "operating_margin": 0.00,
        "ebitda_margin": 0.00,
        "net_margin": 0.00
      }
    }
  },
  
  "balance_sheet": {
    "assets": {
      "total_assets": 0.00,
      "current_assets": {
        "cash_and_equivalents": 0.00,
        "accounts_receivable": 0.00,
        "inventory": 0.00,
        "prepaid_expenses": 0.00,
        "total_current": 0.00
      },
      "non_current_assets": {
        "property_equipment": 0.00,
        "intangible_assets": 0.00,
        "investments": 0.00,
        "total_non_current": 0.00
      }
    },
    "liabilities": {
      "total_liabilities": 0.00,
      "current_liabilities": {
        "accounts_payable": 0.00,
        "accrued_expenses": 0.00,
        "short_term_debt": 0.00,
        "total_current": 0.00
      },
      "long_term_liabilities": {
        "long_term_debt": 0.00,
        "deferred_tax": 0.00,
        "other_long_term": 0.00,
        "total_long_term": 0.00
      }
    },
    "equity": {
      "total_equity": 0.00,
      "owner_equity": 0.00,
      "retained_earnings": 0.00,
      "current_year_earnings": 0.00
    }
  },
  
  "cash_flow_analysis": {
    "operating_activities": {
      "net_cash_from_operations": 0.00,
      "cash_conversion_efficiency": 0.00,
      "operating_cash_margin": 0.00
    },
    "investing_activities": {
      "capital_expenditures": 0.00,
      "asset_disposals": 0.00,
      "net_investing_cash_flow": 0.00
    },
    "financing_activities": {
      "debt_changes": 0.00,
      "equity_changes": 0.00,
      "dividends_distributions": 0.00,
      "net_financing_cash_flow": 0.00
    },
    "cash_position": {
      "beginning_cash": 0.00,
      "ending_cash": 0.00,
      "net_change_in_cash": 0.00,
      "free_cash_flow": 0.00
    }
  },
  
  "working_capital_management": {
    "working_capital_metrics": {
      "gross_working_capital": 0.00,
      "net_working_capital": 0.00,
      "working_capital_ratio": 0.00,
      "working_capital_turnover": 0.00
    },
    "ar_aging_analysis": {
      "total_receivables": 0.00,
      "current_0_30_days": 0.00,
      "past_due_31_60_days": 0.00,
      "past_due_61_90_days": 0.00,
      "past_due_over_90_days": 0.00,
      "collection_efficiency": 0.00,
      "bad_debt_risk": "low|medium|high"
    },
    "ap_aging_analysis": {
      "total_payables": 0.00,
      "current_0_30_days": 0.00,
      "aging_31_60_days": 0.00,
      "aging_61_90_days": 0.00,
      "aging_over_90_days": 0.00,
      "payment_performance": "excellent|good|poor"
    },
    "cash_conversion_cycle": {
      "days_sales_outstanding": 0.00,
      "days_inventory_outstanding": 0.00,
      "days_payable_outstanding": 0.00,
      "cash_cycle_days": 0.00,
      "cycle_efficiency": "excellent|good|needs_improvement"
    }
  },
  
  "financial_ratios": {
    "profitability_ratios": {
      "gross_profit_margin": 0.00,
      "operating_profit_margin": 0.00,
      "net_profit_margin": 0.00,
      "return_on_assets": 0.00,
      "return_on_equity": 0.00,
      "return_on_invested_capital": 0.00
    },
    "liquidity_ratios": {
      "current_ratio": 0.00,
      "quick_ratio": 0.00,
      "cash_ratio": 0.00,
      "operating_cash_flow_ratio": 0.00
    },
    "efficiency_ratios": {
      "asset_turnover": 0.00,
      "inventory_turnover": 0.00,
      "receivables_turnover": 0.00,
      "payables_turnover": 0.00
    },
    "leverage_ratios": {
      "debt_to_equity": 0.00,
      "debt_to_assets": 0.00,
      "interest_coverage": 0.00,
      "debt_service_coverage": 0.00
    }
  },
  
  "what_if_scenarios": {
    "revenue_impact_analysis": {
      "baseline_scenario": {
        "revenue": 0.00,
        "net_income": 0.00,
        "cash_flow": 0.00
      },
      "revenue_decrease_10_percent": {
        "revenue": 0.00,
        "net_income": 0.00,
        "cash_flow": 0.00,
        "impact_assessment": "minimal|moderate|severe"
      },
      "revenue_decrease_20_percent": {
        "revenue": 0.00,
        "net_income": 0.00,
        "cash_flow": 0.00,
        "impact_assessment": "minimal|moderate|severe"
      },
      "revenue_decrease_30_percent": {
        "revenue": 0.00,
        "net_income": 0.00,
        "cash_flow": 0.00,
        "impact_assessment": "minimal|moderate|severe"
      },
      "revenue_increase_20_percent": {
        "revenue": 0.00,
        "net_income": 0.00,
        "cash_flow": 0.00,
        "scalability_constraints": []
      }
    },
    "cost_optimization_scenarios": {
      "fixed_cost_reduction_15_percent": {
        "cost_savings": 0.00,
        "net_income_impact": 0.00,
        "feasibility": "high|medium|low"
      },
      "variable_cost_optimization_10_percent": {
        "cost_savings": 0.00,
        "margin_improvement": 0.00,
        "implementation_difficulty": "easy|moderate|challenging"
      }
    },
    "cash_flow_stress_testing": {
      "best_case_scenario": {
        "months_of_runway": 0,
        "peak_cash_position": 0.00
      },
      "worst_case_scenario": {
        "months_of_runway": 0,
        "cash_shortage_risk": "none|low|medium|high|critical"
      },
      "break_even_analysis": {
        "break_even_revenue": 0.00,
        "margin_of_safety": 0.00,
        "operating_leverage": 0.00
      }
    }
  },
  
  "ai_powered_insights": {
    "trend_analysis": [
      {
        "metric": "revenue",
        "trend_direction": "increasing|stable|declining",
        "trend_strength": "strong|moderate|weak",
        "statistical_confidence": 0.00,
        "forecast_next_period": 0.00,
        "key_drivers": []
      }
    ],
    "anomaly_detection": [
      {
        "metric": "expense_category",
        "anomaly_type": "spike|drop|pattern_break",
        "severity": "critical|high|medium|low",
        "deviation_percentage": 0.00,
        "root_cause_hypothesis": "",
        "recommended_investigation": ""
      }
    ],
    "pattern_recognition": [
      {
        "pattern_type": "seasonal|cyclical|irregular",
        "pattern_description": "",
        "business_impact": "positive|negative|neutral",
        "seasonality_index": 0.00,
        "optimization_opportunity": ""
      }
    ],
    "predictive_alerts": [
      {
        "alert_type": "cash_flow|profitability|liquidity|efficiency",
        "alert_level": "green|yellow|orange|red",
        "forecast_horizon": "1_month|3_months|6_months|12_months",
        "probability": 0.00,
        "potential_impact": 0.00,
        "preventive_actions": []
      }
    ],
    "performance_benchmarking": {
      "industry_comparison": {
        "gross_margin_percentile": 0.00,
        "operating_efficiency_rank": "top_quartile|above_average|below_average|bottom_quartile",
        "cash_management_score": 0.00
      }
    }
  },
  
  "strategic_recommendations": {
    "immediate_actions_0_30_days": [
      {
        "priority": "critical|high|medium",
        "action": "",
        "expected_impact": 0.00,
        "implementation_cost": 0.00,
        "success_metrics": []
      }
    ],
    "short_term_improvements_1_6_months": [
      {
        "initiative": "",
        "business_case": "",
        "investment_required": 0.00,
        "expected_roi": 0.00,
        "risk_factors": []
      }
    ],
    "long_term_strategic_initiatives_6_24_months": [
      {
        "strategic_objective": "",
        "investment_timeline": "",
        "expected_outcomes": [],
        "success_criteria": [],
        "risk_mitigation": []
      }
    ],
    "growth_opportunities": [
      {
        "opportunity_type": "market_expansion|product_development|operational_efficiency|strategic_partnership",
        "revenue_potential": 0.00,
        "investment_required": 0.00,
        "timeline_to_impact": "",
        "feasibility_score": 0.00
      }
    ],
    "risk_mitigation_strategies": [
      {
        "risk_category": "financial|operational|market|regulatory",
        "risk_level": "high|medium|low",
        "mitigation_approach": "",
        "cost_of_mitigation": 0.00,
        "monitoring_metrics": []
      }
    ]
  },
  
  "executive_dashboard_kpis": {
    "financial_health_score": 0.00,
    "burn_rate_months_remaining": 0.00,
    "revenue_growth_rate": 0.00,
    "customer_acquisition_efficiency": 0.00,
    "operational_excellence_score": 0.00,
    "competitive_position_strength": 0.00
  },
  
  "key_insights_summary": [
    "Most critical finding requiring immediate attention",
    "Primary growth opportunity identified",
    "Key operational efficiency improvement",
    "Main financial risk to monitor",
    "Strategic recommendation for long-term success"
  ]
}
```

MANDATORY PROFESSIONAL STANDARDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. EXECUTIVE-LEVEL INSIGHTS: Provide C-suite quality analysis that business owners can confidently present to investors, lenders, or board members.

2. ACTIONABLE INTELLIGENCE: Every insight must include specific, measurable actions with clear implementation pathways and expected outcomes.

3. RISK-AWARE ANALYSIS: Identify and quantify financial risks while providing practical mitigation strategies.

4. GROWTH-ORIENTED PERSPECTIVE: Balance financial prudence with growth opportunities, providing clear pathways for sustainable business expansion.

5. INDUSTRY CONTEXT: Consider industry-specific factors, seasonal patterns, and market conditions in all analyses.

6. CASH FLOW PRIMACY: Prioritize cash flow analysis as the lifeblood of business operations, with detailed runway calculations and cash optimization strategies.

REQUIREMENTS:
- Extract precise financial data from any document format (Excel, PDF, CSV, images, etc.)
- Provide comprehensive what-if scenario modeling for strategic planning
- Generate executive-ready insights suitable for investor presentations
- Include statistical confidence levels for all trend analysis
- Ensure all financial calculations follow GAAP principles
- Return complete JSON structure with all sections populated
- Focus on actionable recommendations that drive measurable business outcomes

Remember: You are the trusted financial advisor that business owners rely on for making million-dollar decisions. Your analysis should be thorough, accurate, and strategically sound.
"""

def analyze_financial_data(financial_data, file_type='excel'):
    """Send data to LLM for analysis"""
    try:
        system_prompt = create_system_prompt()
        
        file_type_map = {'excel': 'Excel', 'pdf': 'PDF', 'csv': 'CSV'}
        file_type_text = file_type_map.get(file_type, file_type.upper())
        user_message = f"""
Analyze this {file_type_text} financial data and return JSON analysis:

{financial_data}

IMPORTANT: Return ONLY valid JSON. No explanations, no markdown, no additional text. Just the JSON object.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
           
        )
        
        analysis_result = response.choices[0].message.content
        if analysis_result is None:
            print("ERROR: AI returned None response")
            return {"error": "AI model returned empty response"}
        
        analysis_result = analysis_result.strip()
        print(f"Raw AI response length: {len(analysis_result)} characters")
        print("Raw AI response preview:", analysis_result[:300] + "..." if len(analysis_result) > 300 else analysis_result)
        
        # Check if response is empty
        if not analysis_result:
            print("ERROR: AI returned empty response")
            return {"error": "AI model returned empty response"}
        
        # Check if response seems incomplete (should contain all major sections)
        required_sections = ["profit_and_loss", "balance_sheet", "cash_flow_statement", "ar_aging_report", "ap_aging_report"]
        missing_sections = [section for section in required_sections if section not in analysis_result]
        
        if missing_sections:
            print(f"WARNING: Missing sections in response: {missing_sections}")
            print("Full response for debugging:")
            print(analysis_result)
            print("=" * 80)
        
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
            parsed_result = json.loads(analysis_result)
            # Ensure we have all required sections
            return ensure_complete_structure(parsed_result)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Problematic JSON around character {e.pos}:")
            start = max(0, e.pos - 50)
            end = min(len(analysis_result), e.pos + 50)
            print(analysis_result[start:end])
            
            # Check if response was truncated
            if not analysis_result.rstrip().endswith('}'):
                print("Response appears to be truncated. Trying to fix...")
                
                # Try to close the JSON properly
                fixed_response = analysis_result.rstrip()
                
                # Count open and close braces to see how many we need
                open_braces = fixed_response.count('{')
                close_braces = fixed_response.count('}')
                missing_braces = open_braces - close_braces
                
                # If we're missing closing braces, try to add them
                if missing_braces > 0:
                    # Remove any incomplete key-value pair at the end
                    lines = fixed_response.split('\n')
                    while lines and (not lines[-1].strip() or 
                                   lines[-1].strip().endswith(':') or 
                                   lines[-1].strip().endswith(',')):
                        lines.pop()
                    
                    fixed_response = '\n'.join(lines)
                    
                    # Add missing closing braces
                    fixed_response += '\n' + '  ' * (missing_braces - 1) + '}'  * missing_braces
                    
                    try:
                        print("Attempting to parse fixed JSON...")
                        return json.loads(fixed_response)
                    except json.JSONDecodeError:
                        print("Failed to fix truncated JSON")
            
            # Try to find and extract JSON object
            import re
            json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_result, re.DOTALL)
            
            for match in json_matches:
                try:
                    return json.loads(match)
                except:
                    continue
            
            # If all else fails, try simplified complete analysis
            print("Failed to parse complete JSON. Trying simplified analysis...")
            return analyze_financial_data_simplified(financial_data, file_type)
                
    except Exception as e:
        return {"error": f"API call failed: {str(e)}"}

def ensure_complete_structure(parsed_result):
    """Ensure the response has all required sections with simplified structure"""
    
    # Simplified template matching the new system prompt
    complete_template = {
        "profit_and_loss": {
            "total_revenue": 0.00,
            "total_expenses": 0.00,
            "gross_profit": 0.00,
            "net_income": 0.00,
            "revenue_breakdown": {
                "consulting_income": 0.00,
                "cleaning_income": 0.00,
                "other_income": 0.00
            },
            "expense_breakdown": {
                "cogs": 0.00,
                "operating_expenses": 0.00,
                "interest_expense": 0.00
            }
        },
        "balance_sheet": {
            "total_assets": 0.00,
            "total_liabilities": 0.00,
            "total_equity": 0.00,
            "current_assets": 0.00,
            "current_liabilities": 0.00,
            "cash": 0.00,
            "accounts_receivable": 0.00,
            "accounts_payable": 0.00
        },
        "cash_flow_statement": {
            "operating_cash_flow": 0.00,
            "investing_cash_flow": 0.00,
            "financing_cash_flow": 0.00,
            "net_cash_change": 0.00,
            "beginning_cash": 0.00,
            "ending_cash": 0.00
        },
        "financial_ratios": {
            "gross_profit_margin": 0.00,
            "net_profit_margin": 0.00,
            "ebitda_margin": 0.00,
            "current_ratio": 0.00,
            "debt_to_equity": 0.00,
            "return_on_equity": 0.00
        },
        "key_kpis": {
            "ebitda": 0.00,
            "ar_days": 0.00,
            "ap_days": 0.00,
            "working_capital": 0.00,
            "cash_conversion_cycle": 0.00,
            "revenue_growth_rate": 0.00
        },
        "cash_flow_trends": {
            "monthly_operating_cf": [],
            "monthly_free_cf": [],
            "cf_trend": "stable",
            "seasonal_patterns": "none"
        },
        "ar_aging": {
            "total_ar": 0.00,
            "current_30_days": 0.00,
            "past_due_31_90_days": 0.00,
            "past_due_over_90_days": 0.00
        },
        "ap_aging": {
            "total_ap": 0.00,
            "current_30_days": 0.00,
            "past_due_31_90_days": 0.00,
            "past_due_over_90_days": 0.00
        },
        "key_insights": [
            "Financial analysis completed based on available data",
            "Key metrics have been calculated", 
            "Review data for accuracy"
        ],
        "ai_powered_insights": {
            "trend_analysis": [
                {"metric": "revenue", "trend": "stable", "confidence": "medium", "description": "Revenue baseline established"}
            ],
            "anomaly_detection": [
                {"metric": "general", "anomaly_type": "none", "severity": "low", "description": "No significant anomalies detected", "recommendation": "Continue monitoring"}
            ],
            "pattern_recognition": [
                {"pattern_type": "baseline", "description": "Establishing baseline patterns for future comparison", "impact": "neutral"}
            ],
            "predictive_insights": [
                {"forecast": "performance", "prediction": "stable", "timeframe": "next_period", "confidence": "low", "action_required": "Gather more historical data for better predictions"}
            ]
        }
    }
    
    def deep_merge(base_dict, update_dict):
        """Recursively merge dictionaries, preserving actual values from update_dict"""
        for key, value in update_dict.items():
            if key in base_dict:
                if isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_merge(base_dict[key], value)
                else:
                    base_dict[key] = value
            else:
                base_dict[key] = value
        return base_dict
    
    # Handle different response formats and convert to simplified structure
    if "total_revenue" in parsed_result and "profit_and_loss" not in parsed_result:
        # AI returned simplified P&L data at root level - wrap it
        complete_template["profit_and_loss"] = parsed_result
    elif "revenue" in parsed_result and "profit_and_loss" not in parsed_result:
        # Old format with nested structures - convert to simplified format
        print("Converting old format to simplified structure...")
        
        # Extract revenue data
        revenue_data = parsed_result.get("revenue", {})
        complete_template["profit_and_loss"]["total_revenue"] = revenue_data.get("total_revenue", 0.00)
        complete_template["profit_and_loss"]["revenue_breakdown"]["consulting_income"] = revenue_data.get("consulting_income", 0.00)
        complete_template["profit_and_loss"]["revenue_breakdown"]["cleaning_income"] = revenue_data.get("cleaning_income", 0.00)
        complete_template["profit_and_loss"]["revenue_breakdown"]["other_income"] = revenue_data.get("app_income", 0.00) + revenue_data.get("other_revenue", 0.00)
        
        # Extract expense data
        cogs_data = parsed_result.get("cost_of_goods_sold", {})
        operating_expenses_data = parsed_result.get("operating_expenses", {})
        other_expenses_data = parsed_result.get("other_income_expense", {})
        
        total_cogs = cogs_data.get("total_cogs", 0.00)
        total_operating_expenses = operating_expenses_data.get("total_operating_expenses", 0.00)
        interest_expense = other_expenses_data.get("interest_expense", 0.00)
        
        complete_template["profit_and_loss"]["total_expenses"] = total_cogs + total_operating_expenses + interest_expense
        complete_template["profit_and_loss"]["expense_breakdown"]["cogs"] = total_cogs
        complete_template["profit_and_loss"]["expense_breakdown"]["operating_expenses"] = total_operating_expenses
        complete_template["profit_and_loss"]["expense_breakdown"]["interest_expense"] = interest_expense
        
        # Extract other financial data
        complete_template["profit_and_loss"]["gross_profit"] = parsed_result.get("gross_profit", 0.00)
        complete_template["profit_and_loss"]["net_income"] = parsed_result.get("net_income", 0.00)
        
        # Calculate financial ratios and KPIs from the data
        total_revenue = complete_template["profit_and_loss"]["total_revenue"]
        gross_profit = complete_template["profit_and_loss"]["gross_profit"] 
        net_income = complete_template["profit_and_loss"]["net_income"]
        total_cogs = complete_template["profit_and_loss"]["expense_breakdown"]["cogs"]
        
        # Extract depreciation if available (from operating expenses)
        depreciation = parsed_result.get("operating_expenses", {}).get("depreciation", 0.00)
        interest_expense = complete_template["profit_and_loss"]["expense_breakdown"]["interest_expense"]
        
        # Calculate EBITDA
        ebitda = net_income + interest_expense + 0 + depreciation  # Assuming no taxes separately tracked
        complete_template["key_kpis"]["ebitda"] = ebitda
        
        if total_revenue > 0:
            complete_template["financial_ratios"]["gross_profit_margin"] = round((gross_profit / total_revenue) * 100, 2)
            complete_template["financial_ratios"]["net_profit_margin"] = round((net_income / total_revenue) * 100, 2)
            complete_template["financial_ratios"]["ebitda_margin"] = round((ebitda / total_revenue) * 100, 2)
        
        # Calculate working capital KPIs (basic estimates)
        current_assets = complete_template["balance_sheet"]["current_assets"]
        current_liabilities = complete_template["balance_sheet"]["current_liabilities"]
        accounts_receivable = complete_template["balance_sheet"]["accounts_receivable"]
        accounts_payable = complete_template["balance_sheet"]["accounts_payable"]
        
        complete_template["key_kpis"]["working_capital"] = current_assets - current_liabilities
        
        # Calculate AR and AP days if we have the data
        if total_revenue > 0 and accounts_receivable > 0:
            complete_template["key_kpis"]["ar_days"] = round((accounts_receivable / total_revenue) * 365, 1)
        
        if total_cogs > 0 and accounts_payable > 0:
            complete_template["key_kpis"]["ap_days"] = round((accounts_payable / total_cogs) * 365, 1)
        
        # Calculate cash conversion cycle
        ar_days = complete_template["key_kpis"]["ar_days"]
        ap_days = complete_template["key_kpis"]["ap_days"]
        inventory_days = 0  # Simplified - could be calculated if inventory data available
        complete_template["key_kpis"]["cash_conversion_cycle"] = ar_days + inventory_days - ap_days
        
        # Add key insights based on the data including KPIs
        insights = []
        insights.append(f"Revenue: ${total_revenue:,.2f}, Net Income: ${net_income:,.2f}")
        insights.append(f"EBITDA: ${ebitda:,.2f} ({complete_template['financial_ratios']['ebitda_margin']}% margin)")
        
        if complete_template["key_kpis"]["ar_days"] > 0:
            insights.append(f"AR Days: {complete_template['key_kpis']['ar_days']} days")
        else:
            insights.append("Gross Profit Margin: {:.1f}%".format(complete_template['financial_ratios']['gross_profit_margin']))
            
        complete_template["key_insights"] = insights
        
        # Add AI-powered trend and anomaly analysis
        ai_insights = {
            "trend_analysis": [],
            "anomaly_detection": [],
            "pattern_recognition": [],
            "predictive_insights": []
        }
        
        # Revenue trend analysis
        if total_revenue > 0:
            if net_income < 0:
                ai_insights["trend_analysis"].append({
                    "metric": "profitability",
                    "trend": "declining", 
                    "confidence": "high",
                    "description": f"Company operating at a loss with negative net income of ${net_income:,.2f}"
                })
            else:
                ai_insights["trend_analysis"].append({
                    "metric": "profitability",
                    "trend": "positive",
                    "confidence": "high", 
                    "description": f"Profitable operations with net income of ${net_income:,.2f}"
                })
        
        # EBITDA trend analysis  
        if ebitda < 0:
            ai_insights["trend_analysis"].append({
                "metric": "ebitda",
                "trend": "concerning",
                "confidence": "high",
                "description": f"Negative EBITDA of ${ebitda:,.2f} indicates operational challenges"
            })
        
        # Anomaly detection based on financial ratios
        gross_margin = complete_template['financial_ratios']['gross_profit_margin']
        net_margin = complete_template['financial_ratios']['net_profit_margin'] 
        
        if gross_margin > 70:
            ai_insights["anomaly_detection"].append({
                "metric": "gross_margin",
                "anomaly_type": "high_margin", 
                "severity": "medium",
                "description": f"Unusually high gross margin of {gross_margin}% - verify pricing strategy",
                "recommendation": "Review pricing model and cost structure for sustainability"
            })
        elif gross_margin < 20:
            ai_insights["anomaly_detection"].append({
                "metric": "gross_margin",
                "anomaly_type": "low_margin",
                "severity": "high", 
                "description": f"Low gross margin of {gross_margin}% indicates pricing pressure",
                "recommendation": "Optimize costs or increase pricing to improve margins"
            })
        
        # Cash flow predictions
        if net_income < -100000:
            ai_insights["predictive_insights"].append({
                "forecast": "cash_flow",
                "prediction": "negative",
                "timeframe": "next_quarter",
                "confidence": "high",
                "action_required": "Immediate cost reduction and cash flow management required"
            })
        
        # Pattern recognition for expense structure
        if total_revenue > 0:
            expense_ratio = (complete_template["profit_and_loss"]["total_expenses"] / total_revenue) * 100
            if expense_ratio > 150:
                ai_insights["pattern_recognition"].append({
                    "pattern_type": "expense_structure",
                    "description": f"High expense ratio of {expense_ratio:.1f}% indicates operational inefficiencies",
                    "impact": "negative"
                })
        
        complete_template["ai_powered_insights"] = ai_insights
        
        # Set basic balance sheet data (derived from P&L)
        complete_template["balance_sheet"]["total_equity"] = net_income
        complete_template["balance_sheet"]["total_assets"] = max(0, net_income)  # Simplified assumption
        
        # Set cash flow data (basic)
        complete_template["cash_flow_statement"]["operating_cash_flow"] = net_income
        complete_template["cash_flow_statement"]["net_cash_change"] = net_income
        complete_template["cash_flow_statement"]["ending_cash"] = max(0, net_income)
        
    else:
        # Standard simplified format - merge with template
        deep_merge(complete_template, parsed_result)
    
    return complete_template

def extract_partial_data(raw_response, file_type='excel'):
    """Extract whatever valid data we can from a partial/truncated response"""
    try:
        import re
        
        # Try to extract revenue numbers
        revenue_pattern = r'"total_revenue":\s*([\d.]+)'
        expenses_pattern = r'"total_operating_expenses":\s*([\d.]+)'
        net_income_pattern = r'"net_income":\s*(-?[\d.]+)'
        
        total_revenue = 0
        total_expenses = 0  
        net_income = 0
        
        revenue_match = re.search(revenue_pattern, raw_response)
        if revenue_match:
            total_revenue = float(revenue_match.group(1))
            
        expenses_match = re.search(expenses_pattern, raw_response)
        if expenses_match:
            total_expenses = float(expenses_match.group(1))
            
        net_income_match = re.search(net_income_pattern, raw_response)
        if net_income_match:
            net_income = float(net_income_match.group(1))
        
        # Return minimal but complete structure
        return {
            "profit_and_loss": {
                "revenue": {
                    "total_revenue": total_revenue
                },
                "operating_expenses": {
                    "total_operating_expenses": total_expenses
                },
                "net_income": net_income
            },
            "balance_sheet": {
                "assets": {"total_assets": 0},
                "liabilities": {"total_liabilities": 0},
                "equity": {"total_equity": net_income}
            },
            "cash_flow_statement": {
                "operating_activities": {"net_cash_from_operating": net_income},
                "investing_activities": {"net_cash_from_investing": 0},
                "financing_activities": {"net_cash_from_financing": 0}
            },
            "ar_aging_report": {"total_accounts_receivable": 0},
            "ap_aging_report": {"total_accounts_payable": 0},
            "financial_ratios": {"profitability_ratios": {"net_profit_margin": 0}},
            "analysis_status": "partial_data_extracted",
            "issue": "Response was truncated - showing available data only"
        }
        
    except Exception as e:
        return {
            "error": "Could not extract data from truncated response",
            "raw_response_preview": raw_response[:500] if raw_response else "No response"
        }

def analyze_financial_data_simplified(financial_data, file_type='excel'):
    """Simplified analysis that returns the streamlined structure"""
    try:
        simplified_prompt = """
You are a financial analyst. Analyze the financial data and return ONLY this JSON:

{
  "profit_and_loss": {
    "total_revenue": 0.00,
    "total_expenses": 0.00,
    "gross_profit": 0.00,
    "net_income": 0.00,
    "revenue_breakdown": {
      "consulting_income": 0.00,
      "cleaning_income": 0.00,
      "other_income": 0.00
    },
    "expense_breakdown": {
      "cogs": 0.00,
      "operating_expenses": 0.00,
      "interest_expense": 0.00
    }
  },
  "balance_sheet": {
    "total_assets": 0.00,
    "total_liabilities": 0.00,
    "total_equity": 0.00,
    "current_assets": 0.00,
    "current_liabilities": 0.00,
    "cash": 0.00,
    "accounts_receivable": 0.00,
    "accounts_payable": 0.00
  },
  "cash_flow_statement": {
    "operating_cash_flow": 0.00,
    "investing_cash_flow": 0.00,
    "financing_cash_flow": 0.00,
    "net_cash_change": 0.00,
    "beginning_cash": 0.00,
    "ending_cash": 0.00
  },
  "financial_ratios": {
    "gross_profit_margin": 0.00,
    "net_profit_margin": 0.00,
    "ebitda_margin": 0.00,
    "current_ratio": 0.00,
    "debt_to_equity": 0.00,
    "return_on_equity": 0.00
  },
  "key_kpis": {
    "ebitda": 0.00,
    "ar_days": 0.00,
    "ap_days": 0.00,
    "working_capital": 0.00,
    "cash_conversion_cycle": 0.00,
    "revenue_growth_rate": 0.00
  },
  "cash_flow_trends": {
    "monthly_operating_cf": [],
    "monthly_free_cf": [],
    "cf_trend": "stable",
    "seasonal_patterns": "none"
  },
  "ar_aging": {
    "total_ar": 0.00,
    "current_30_days": 0.00,
    "past_due_31_90_days": 0.00,
    "past_due_over_90_days": 0.00
  },
  "ap_aging": {
    "total_ap": 0.00,
    "current_30_days": 0.00,
    "past_due_31_90_days": 0.00,
    "past_due_over_90_days": 0.00
  },
  "key_insights": [
    "Key insight from analysis",
    "Important recommendation", 
    "Notable finding"
  ],
  "ai_powered_insights": {
    "trend_analysis": [
      {
        "metric": "revenue",
        "trend": "increasing",
        "confidence": "high",
        "description": "Revenue showing upward trend over analysis period"
      }
    ],
    "anomaly_detection": [
      {
        "metric": "expenses", 
        "anomaly_type": "spike",
        "severity": "medium",
        "description": "Unusual expense spike detected in operating costs",
        "recommendation": "Review operating expense categories for cost control"
      }
    ],
    "pattern_recognition": [
      {
        "pattern_type": "seasonal",
        "description": "Revenue shows seasonal patterns with Q4 peaks",
        "impact": "positive"
      }
    ],
    "predictive_insights": [
      {
        "forecast": "cash_flow", 
        "prediction": "negative",
        "timeframe": "next_quarter",
        "confidence": "medium",
        "action_required": "Improve collections and reduce expenses"
      }
    ]
  }
}

Extract real numbers from the data. Return valid JSON only."""
        
        file_type_map = {'excel': 'Excel', 'pdf': 'PDF', 'csv': 'CSV'}
        file_type_text = file_type_map.get(file_type, file_type.upper())
        
        user_message = f"Analyze this {file_type_text} financial data:\n\n{financial_data}..."  # Limit input data
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": simplified_prompt},
                {"role": "user", "content": user_message}
            ],
            
        )
        
        result = response.choices[0].message.content
        if result:
            result = result.strip()
            # Remove markdown if present
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            
            return json.loads(result)
        else:
            return {"error": "Simplified analysis also failed"}
            
    except Exception as e:
        return {
            "profit_and_loss": {
                "total_revenue": 0.00,
                "total_expenses": 0.00, 
                "gross_profit": 0.00,
                "net_income": 0.00,
                "revenue_breakdown": {"consulting_income": 0.00, "cleaning_income": 0.00, "other_income": 0.00},
                "expense_breakdown": {"cogs": 0.00, "operating_expenses": 0.00, "interest_expense": 0.00}
            },
            "balance_sheet": {
                "total_assets": 0.00, "total_liabilities": 0.00, "total_equity": 0.00,
                "current_assets": 0.00, "current_liabilities": 0.00, "cash": 0.00,
                "accounts_receivable": 0.00, "accounts_payable": 0.00
            },
            "cash_flow_statement": {
                "operating_cash_flow": 0.00, "investing_cash_flow": 0.00,
                "financing_cash_flow": 0.00, "net_cash_change": 0.00,
                "beginning_cash": 0.00, "ending_cash": 0.00
            },
            "financial_ratios": {
                            "gross_profit_margin": 0.00, "net_profit_margin": 0.00, "ebitda_margin": 0.00,
            "current_ratio": 0.00, "debt_to_equity": 0.00, "return_on_equity": 0.00
        },
        "key_kpis": {
            "ebitda": 0.00, "ar_days": 0.00, "ap_days": 0.00, "working_capital": 0.00,
            "cash_conversion_cycle": 0.00, "revenue_growth_rate": 0.00
        },
        "cash_flow_trends": {
            "monthly_operating_cf": [], "monthly_free_cf": [], "cf_trend": "stable", "seasonal_patterns": "none"
        },
            "ar_aging": {"total_ar": 0.00, "current_30_days": 0.00, "past_due_31_90_days": 0.00, "past_due_over_90_days": 0.00},
            "ap_aging": {"total_ap": 0.00, "current_30_days": 0.00, "past_due_31_90_days": 0.00, "past_due_over_90_days": 0.00},
            "key_insights": ["Analysis failed - manual review required", f"Error: {str(e)}"],
            "ai_powered_insights": {
                "trend_analysis": [{"metric": "error", "trend": "unknown", "confidence": "low", "description": "Unable to analyze trends due to data processing error"}],
                "anomaly_detection": [{"metric": "system", "anomaly_type": "error", "severity": "high", "description": "Analysis system error", "recommendation": "Retry with different data format"}],
                "pattern_recognition": [{"pattern_type": "error", "description": "Pattern analysis unavailable", "impact": "unknown"}],
                "predictive_insights": [{"forecast": "unavailable", "prediction": "unknown", "timeframe": "n/a", "confidence": "none", "action_required": "Fix data processing issues"}]
            },
            "error": f"Both analyses failed: {str(e)}"
        }

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

def main(file_path=None):
    """Main function - can process both Excel and PDF files"""
    # Default to Excel file if no path provided
    if file_path is None:
        file_path = "data/Budget_March.xlsx"
    
    # Read financial file (Excel or PDF)
    print(f"Reading financial file: {file_path}")
    financial_data, file_type = read_financial_file(file_path)
    
    if financial_data is None:
        print(f"Failed to read file: {file_path}")
        return None
    
    # Analyze with LLM
    print("Analyzing data with AI...")
    analysis_result = analyze_financial_data(financial_data, file_type)
    
    # Display results
    display_results(analysis_result)
    
    # Save to file
    if "error" not in analysis_result:
        output_filename = f"financial_analysis_{file_type}.json"
        save_analysis_to_file(analysis_result, output_filename)
    
    return analysis_result

def process_multiple_files(file_paths):
    """Process multiple financial files and combine analysis"""
    all_results = {}
    
    for file_path in file_paths:
        print(f"\n{'='*60}")
        print(f"Processing: {file_path}")
        print(f"{'='*60}")
        
        result = main(file_path)
        if result and "error" not in result:
            filename = os.path.basename(file_path)
            all_results[filename] = result
        
    return all_results

if __name__ == "__main__":
    result = main()