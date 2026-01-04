"""
archetecture.py
Modular agent-based architecture for Excel AI Add-in, inspired by the banking assistant project.
Defines a central AgentRouter and specialized agents for analysis, graphing, and cleaning.
"""
import openai
from typing import List, Dict, Any, Optional
try:
    from .gpt_agent import get_code_from_gpt
    from .code_executor import execute_code
except ImportError:
    from gpt_agent import get_code_from_gpt
    from code_executor import execute_code

# Shared chat log/message structure
def make_message(role: str, content: str) -> Dict[str, str]:
    return {"role": role, "content": content}

class Agent:
    """
    Base class for all agents. Each agent has access to the router, chat log, and data context.
    """
    def __init__(self, router, name: str, system_prompt: str = ""):
        self.router = router
        self.name = name
        self.system_prompt = system_prompt
        self.messages = [make_message("system", system_prompt)] if system_prompt else []

    def process(self, message: str, data: Any = None) -> Any:
        """
        Main entry point for agent logic. Should be overridden by subclasses.
        """
        raise NotImplementedError

    def add_user_message(self, message: str):
        self.messages.append(make_message("user", message))

    def add_assistant_message(self, message: str):
        self.messages.append(make_message("assistant", message))

    def get_history(self) -> List[Dict[str, str]]:
        return self.messages

    def get_display_name(self) -> str:
        return self.name.capitalize() + " Bot"

class AgentRouter:
    """
    Central router that manages chat log, data context, and agent delegation.
    """
    def __init__(self):
        self.chat_log: List[Dict[str, str]] = []
        self.data_context: Optional[Any] = None
        self.current_agent: Optional[str] = None
        self.agents = {
            "sanitizer": PromptSanitizerAgent(self),
            "graph": GraphAgent(self),
            "cleaning": CleaningAgent(self),
            "question": QuestionAgent(self),
            "formula": FormulaAgent(self),
            "assistant": AssistantAgent(self),
        }

    def handle_user_message(self, message: str, data: Any = None) -> Any:
        self.chat_log.append(make_message("user", message))
        self.data_context = data
        # First sanitize and classify the request
        self.current_agent = "sanitizer"
        sanitized = self.agents["sanitizer"].process(message, data)
        if isinstance(sanitized, dict):
            intent = sanitized.get("intent", "chat")
            task = sanitized.get("task", {})
        else:
            intent = "chat"
            task = {"prompt": str(sanitized)}

        if intent == "graph":
            self.current_agent = "graph"
            return self.agents["graph"].process(task.get("prompt", message), data)
        if intent == "clean":
            self.current_agent = "cleaning"
            return self.agents["cleaning"].process(task.get("prompt", message), data)
        if intent == "question":
            self.current_agent = "question"
            return self.agents["question"].process(task.get("prompt", message), data)
        self.current_agent = "sanitizer"
        return "I'm here to help! Please specify if you want to analyze, graph, clean, or ask questions about your data."
    
    def process_with_agent(self, agent_type: str, message: str, data: Any = None) -> Any:
        """Process request with specific agent - completely separate, no mixing"""
        self.chat_log.append(make_message("user", message))
        self.data_context = data
        self.current_agent = agent_type
        
        # Each agent handles its own logic completely independently
        if agent_type == "graph":
            return self.agents["graph"].process(message, data)
        elif agent_type == "cleaning":
            return self.agents["cleaning"].process(message, data)
        elif agent_type == "formula":
            return self.agents["formula"].process(message, data)
        elif agent_type == "assistant":
            return self.agents["assistant"].process(message, data)
        else:
            # Default to assistant for unknown types
            return self.agents["assistant"].process(message, data)
    
    def get_agent_display_name(self, agent_type: str) -> str:
        """Get the display name of the selected agent"""
        names = {
            "graph": "Graph Agent",
            "cleaning": "Cleaning Agent", 
            "formula": "Formula Agent",
            "assistant": "General Assistant",
            "question": "Question Agent"
        }
        return names.get(agent_type, "General Assistant")

    def set_current_agent(self, agent_name: str):
        self.current_agent = agent_name

    def get_current_agent_display_name(self) -> str:
        if self.current_agent and self.current_agent in self.agents:
            return self.agents[self.current_agent].get_display_name()
        return "AI Analyst Bot"

    def add_agent_message(self, agent_name: str, message: str):
        self.chat_log.append(make_message(agent_name, message))

    def get_chat_log(self) -> List[Dict[str, str]]:
        return self.chat_log

    def get_data_context(self) -> Any:
        return self.data_context

class PromptSanitizerAgent(Agent):
    def __init__(self, router):
        super().__init__(router, name="sanitizer", system_prompt=(
            "You are a prompt sanitizer for an Excel AI assistant. "
            "Your job is to clarify and improve user requests to make them more specific and actionable. "
            "Analyze the user's intent and create a clearer, more focused prompt. "
            "Return a JSON object with: intent (string), task (object with improved 'prompt'). "
            "Make the prompt more specific and actionable while preserving the user's original intent."
        ))

    def process(self, message: str, data: Any = None) -> Any:
        try:
            from .gpt_agent import call_gpt
        except ImportError:
            from gpt_agent import call_gpt
        
        # Build data context for sanitization
        data_context = ""
        if data is not None:
            try:
                if hasattr(data, 'shape'):
                    data_context = f"Data shape: {data.shape}\n"
                if hasattr(data, 'columns'):
                    data_context += f"Columns: {list(data.columns)}\n"
                if hasattr(data, 'head'):
                    data_context += f"Sample data:\n{data.head().to_string()}"
            except:
                data_context = f"Data: {str(data)[:500]}"
        
        prompt = f"""You are a prompt sanitizer for an Excel AI assistant. Your job is to clarify and improve user requests.

Original user request: "{message}"

Data context:
{data_context}

Please:
1. Identify the user's intent (graph, clean, question, or general)
2. Create a clearer, more specific prompt that will help the AI assistant understand exactly what to do
3. Make the request more actionable while preserving the user's original intent

Return a JSON object with:
- "intent": the identified intent (string)
- "task": an object with "prompt" containing the improved, clearer request

Example:
User: "make it look better"
Improved: "Clean and standardize the data formatting, remove extra spaces, and ensure consistent data types"

Return only the JSON object."""
        
        try:
            sanitized_response = call_gpt(prompt)
            # Try to parse the JSON response
            import json
            result = json.loads(sanitized_response)
            return result
        except:
            # Fallback to simple keyword detection
            msg = message.lower().strip()
            if any(w in msg for w in ["graph", "plot", "chart", "visualize"]):
                intent = "graph"
            elif any(w in msg for w in ["clean", "tidy", "fix", "remove missing", "fill missing"]):
                intent = "clean"
            elif any(w in msg for w in ["what", "how", "average", "mean", "sum", "count", "max", "min", "total", "calculate", "analyze", "tell me", "explain"]):
                intent = "question"
            else:
                intent = "chat"
            
            return {
                "intent": intent,
                "task": {"prompt": message.strip()}
            }

class GraphAgent(Agent):
    def __init__(self, router):
        super().__init__(router, name="graph", system_prompt=(
            "You are the Graph Agent for an Excel AI add-in. "
            "Your job is to generate Python code or images for data visualizations based on the user's request and the provided data. "
            "Always use the provided data context. "
            "Return ONLY the code or image, with no extra explanation or formatting."
        ))

    def process(self, message: str, data: Any = None) -> Any:
        """Graph Agent - ONLY creates visualizations, no questions or analysis"""
        try:
            df_head = data.head().to_string(index=False) if hasattr(data, 'head') else str(data)[:1000]
        except Exception:
            df_head = str(data)[:1000]

        # Get code from GPT and execute it against the provided DataFrame
        code = get_code_from_gpt(message, df_head)
        exec_result = execute_code(code, data)

        if isinstance(exec_result, dict) and 'error' in exec_result:
            return {"error": exec_result['error']}

        # If a chart was created, the server will capture it; return a friendly text
        if isinstance(exec_result, dict) and exec_result.get('chart_created'):
            return {"result": "Chart created successfully!"}

        # Otherwise return any textual result from the executed code
        return {"result": "Code executed."}

class FormulaAgent(Agent):
    def __init__(self, router):
        super().__init__(router, name="formula", system_prompt=(
            "You are the Formula Agent for an Excel AI add-in. "
            "Your job is to create Excel formulas and perform calculations. "
            "Always provide clear, working Excel formulas and explain what they do."
        ))

    def process(self, message: str, data: Any = None) -> Any:
        """Formula Agent - ONLY creates formulas and calculations"""
        try:
            from .gpt_agent import call_gpt
        except ImportError:
            from gpt_agent import call_gpt
        
        # Build data summary for formula creation
        data_summary = f"Data shape: {data.shape if hasattr(data, 'shape') else 'Unknown'}\n"
        if hasattr(data, 'columns'):
            data_summary += f"Columns: {list(data.columns)}\n"
        if hasattr(data, 'head'):
            data_summary += f"Sample data:\n{data.head().to_string()}"
        
        prompt = f"""You are an Excel formula expert. Create Excel formulas based on the user's request.

User request: {message}
Data context:
{data_summary}

Provide Excel formulas that will work with this data. Explain what each formula does and how to use it."""
        
        answer = call_gpt(prompt)
        return {"result": answer}

class AssistantAgent(Agent):
    def __init__(self, router):
        super().__init__(router, name="assistant", system_prompt=(
            "You are a professional data analyst. Give concise, direct answers. "
            "Be brief and practical. Avoid academic language or lengthy explanations."
        ))

    def process(self, message: str, data: Any = None) -> Any:
        """Assistant Agent - ONLY answers questions and provides analysis"""
        try:
            from .gpt_agent import call_gpt
        except ImportError:
            from gpt_agent import call_gpt
        
        # Build data summary for analysis
        data_summary = f"Data shape: {data.shape if hasattr(data, 'shape') else 'Unknown'}\n"
        if hasattr(data, 'columns'):
            data_summary += f"Columns: {list(data.columns)}\n"
        if hasattr(data, 'head'):
            data_summary += f"Sample data:\n{data.head().to_string()}"
        
        prompt = f"""Answer this question about the data. Be brief and direct.

Question: {message}
Data: {data_summary}

Give a short, practical answer. No lengthy explanations."""
        
        answer = call_gpt(prompt)
        return {"result": answer}

class CleaningAgent(Agent):
    def __init__(self, router):
        super().__init__(router, name="cleaning", system_prompt=(
            "You are the Cleaning Agent for an Excel AI add-in. "
            "Your job is to clean and tidy up tabular data as requested by the user. "
            "This includes filling missing values, correcting invalid numbers, and fixing date formats. "
            "Always return ONLY the cleaned table in Markdown format, with the same headers and number of rows as the input. "
            "Do not include any explanations or extra text."
        ))

    def process(self, message: str, data: Any = None) -> Any:
        try:
            # Get data summary for GPT
            if hasattr(data, 'describe'):
                data_summary = f"Data shape: {data.shape}\nColumns: {list(data.columns)}\nMissing values:\n{data.isnull().sum()}\nData preview:\n{data.head().to_string()}"
            elif hasattr(data, 'head'):
                data_summary = f"Data preview:\n{data.head().to_string()}"
            else:
                data_summary = str(data)[:1000]

            # Get cleaning instructions from GPT
            try:
                try:
                    from .gpt_agent import call_gpt
                except ImportError:
                    from gpt_agent import call_gpt
                
                prompt = f"""You are a data cleaning expert. Given the user's request and data, provide Python code to clean the data.

User request: {message}
Data:
{data_summary}

Return ONLY Python code that:
1. Takes the DataFrame 'df' as input
2. Performs the requested cleaning operation
3. Stores the result in a variable called 'df_cleaned'
4. Use appropriate methods like fillna(), dropna(), etc.
5. DO NOT use 'return' statements - just assign to 'df_cleaned'
6. Handle mixed data types safely - check data types before operations
7. For numeric operations, use pd.to_numeric() with errors='coerce' to handle text
8. If no missing values exist, still perform data standardization/cleaning

IMPORTANT: Even if there are no missing values, still clean the data by:
- Standardizing text formats
- Converting data types appropriately
- Removing extra spaces
- Handling inconsistent values

Example for comprehensive data cleaning:
```python
# Comprehensive data cleaning
df_cleaned = df.copy()

for col in df_cleaned.columns:
    # Clean text data
    if df_cleaned[col].dtype in ['object', 'string']:
        # Remove extra spaces and standardize
        df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
        # Fill any empty strings or 'nan' values
        df_cleaned[col] = df_cleaned[col].replace(['', 'nan', 'NaN'], pd.NA)
        # Fill missing values with mode or 'Unknown'
        mode_value = df_cleaned[col].mode()
        if len(mode_value) > 0 and not pd.isna(mode_value[0]):
            df_cleaned[col] = df_cleaned[col].fillna(mode_value[0])
        else:
            df_cleaned[col] = df_cleaned[col].fillna('Unknown')
    else:
        # For numeric columns, try to convert and clean
        try:
            numeric_col = pd.to_numeric(df_cleaned[col], errors='coerce')
            df_cleaned[col] = numeric_col.fillna(numeric_col.median())
        except:
            df_cleaned[col] = df_cleaned[col].fillna(df_cleaned[col].median())
```"""

                cleaning_code = call_gpt(prompt)
                
                # Execute the cleaning code
                local_vars = {}
                global_vars = {
                    "df": data,
                    "pd": __import__('pandas'),
                    "numpy": __import__('numpy'),
                    "np": __import__('numpy')
                }
                
                # Clean the code (remove markdown formatting and return statements)
                import re
                cleaning_code = re.sub(r'```python\s*', '', cleaning_code)
                cleaning_code = re.sub(r'```\s*$', '', cleaning_code).strip()
                # Remove any return statements that might cause issues
                cleaning_code = re.sub(r'return\s+.*', '', cleaning_code)
                
                try:
                    exec(cleaning_code, global_vars, local_vars)
                    
                    # Get the cleaned DataFrame
                    if 'df_cleaned' in local_vars:
                        cleaned_df = local_vars['df_cleaned']
                    else:
                        # Fallback: use original data if cleaning failed
                        cleaned_df = data
                        
                except Exception as exec_error:
                    # If execution fails, try a simpler approach
                    try:
                        # Simple fallback: just fill missing values with appropriate defaults
                        cleaned_df = data.copy() if hasattr(data, 'copy') else data
                        if hasattr(cleaned_df, 'fillna'):
                            for col in cleaned_df.columns:
                                if cleaned_df[col].dtype in ['object', 'string']:
                                    cleaned_df[col] = cleaned_df[col].fillna('Unknown')
                                else:
                                    cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())
                    except:
                        cleaned_df = data
                
                # Generate reasoning
                reasoning = self._generate_reasoning(message, data, cleaned_df)
                
                # Prepare cell-based updates for Excel
                try:
                    if hasattr(cleaned_df, 'values'):
                        # Find cells that changed and their coordinates
                        cell_updates = []
                        
                        # Compare original vs cleaned data
                        for row_idx in range(len(data)):
                            for col_idx in range(len(data[row_idx])):
                                try:
                                    original_val = data[row_idx][col_idx]
                                    # Safely get cleaned value
                                    if (row_idx < len(cleaned_df) and 
                                        col_idx < len(cleaned_df.columns) and
                                        hasattr(cleaned_df, 'iloc')):
                                        cleaned_val = cleaned_df.iloc[row_idx, col_idx]
                                    else:
                                        cleaned_val = original_val
                                    
                                    # Check if value changed (handle NaN values)
                                    original_str = str(original_val) if original_val is not None else ""
                                    cleaned_str = str(cleaned_val) if cleaned_val is not None else ""
                                    
                                    if original_str != cleaned_str:
                                        cell_updates.append({
                                            "row": row_idx,
                                            "col": col_idx,
                                            "value": cleaned_val
                                        })
                                except Exception as cell_error:
                                    # Skip problematic cells but continue processing
                                    continue
                        
                        if cell_updates:
                            return {
                                "result": f"Data cleaned successfully!\n\n{reasoning}",
                                "cell_updates": cell_updates,
                                "action": "update_cells"  # Signal to frontend to update specific cells
                            }
                        else:
                            return {
                                "result": f"Data was already clean!\n\n{reasoning}",
                                "action": "no_changes"
                            }
                    else:
                        return {
                            "result": f"Data cleaned successfully!\n\n{reasoning}",
                            "cleaned_data": str(cleaned_df)
                        }
                except Exception as update_error:
                    return {
                        "result": f"Data cleaned but had issues with cell updates: {str(update_error)}\n\n{reasoning}",
                        "action": "no_changes"
                    }
                
            except Exception as e:
                return {"result": f"Cleaning failed: {str(e)}"}
                
        except Exception as e:
            return {"result": f"Error processing cleaning request: {str(e)}"}
    
    def _generate_reasoning(self, message: str, original_data, cleaned_data):
        """Generate reasoning for the cleaning operation"""
        try:
            original_missing = original_data.isnull().sum().sum() if hasattr(original_data, 'isnull') else 0
            cleaned_missing = cleaned_data.isnull().sum().sum() if hasattr(cleaned_data, 'isnull') else 0
            changes_made = []
            
            reasoning = f"Cleaning Summary:\n"
            reasoning += f"- Original missing values: {original_missing}\n"
            reasoning += f"- Remaining missing values: {cleaned_missing}\n"
            reasoning += f"- Values filled: {original_missing - cleaned_missing}\n"
            
            # Check for other types of cleaning
            if hasattr(original_data, 'dtypes') and hasattr(cleaned_data, 'dtypes'):
                for col in original_data.columns:
                    if col in cleaned_data.columns:
                        # Check if data types changed
                        if str(original_data[col].dtype) != str(cleaned_data[col].dtype):
                            changes_made.append(f"Column '{col}': {original_data[col].dtype} → {cleaned_data[col].dtype}")
                        
                        # Check for text standardization
                        if original_data[col].dtype == 'object':
                            orig_str = original_data[col].astype(str).str.strip()
                            clean_str = cleaned_data[col].astype(str).str.strip()
                            if not orig_str.equals(clean_str):
                                changes_made.append(f"Column '{col}': Text standardized and cleaned")
            
            if "fill" in message.lower() or "missing" in message.lower():
                reasoning += f"- Method used: Filled missing values with appropriate defaults\n"
            else:
                reasoning += f"- Method used: Comprehensive data cleaning with standardization\n"
            
            if changes_made:
                reasoning += f"\nAdditional improvements:\n" + "\n".join(f"- {change}" for change in changes_made)
            elif original_missing == 0:
                reasoning += f"\nNote: Data was already clean, but standardized for consistency."
            
            return reasoning
        except:
            return "Data cleaning completed using AI-determined methods."

class QuestionAgent(Agent):
    def __init__(self, router):
        super().__init__(router, name="question", system_prompt=(
            "You are a data analyst. Answer questions directly and briefly. "
            "Give practical insights without lengthy explanations."
        ))

    def process(self, message: str, data: Any = None) -> Any:
        # Build a data summary for GPT
        try:
            if hasattr(data, 'describe'):
                data_summary = f"Data shape: {data.shape}\nColumns: {list(data.columns)}\nSummary:\n{data.describe()}"
            elif hasattr(data, 'head'):
                data_summary = f"Data preview:\n{data.head().to_string()}"
            else:
                data_summary = str(data)[:1000]
        except Exception:
            data_summary = str(data)[:1000]

        # Get answer from GPT

        prompt = f"{self.system_prompt}\n\nQuestion: {message}\nData:\n{data_summary}\n\nGive a brief, direct answer:"
        
        try:
            try:
                from .gpt_agent import call_gpt
            except ImportError:
                from gpt_agent import call_gpt
            answer = call_gpt(prompt)
            return {"result": answer}
        except Exception as e:
            return {"result": f"I can help analyze your data, but encountered an error: {str(e)}"}

# Example usage (for integration in server.py):
# router = AgentRouter()
# result = router.handle_user_message(user_message, data_context)
# print(result)
# print(router.get_current_agent_display_name()) 