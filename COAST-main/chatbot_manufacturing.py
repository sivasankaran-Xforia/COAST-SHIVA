import os 
from openai import OpenAI
from dotenv import load_dotenv
from config import PROMPT_TEMPLATE_FILE

load_dotenv()

# Get the API key from the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

# Initialize the OpenAI client with the environment variable
client = OpenAI(api_key=OPENAI_API_KEY)

#LLM_TEXT_FILE = r"/Users/harishreekarthik/Downloads/Xforia_COAST/demo/CAD_knowledge_all.txt"

def process_manufacturing_chat(user_query: str, context_file: str, conversation_history: list[dict] = None) -> str: 
    """
    Retrieves the combined data from the prepared text file and uses it
    to ground an LLM's response, including a vendor scoring system.

    Args:
        user_query (str): The user's question or command.

    Returns: 
        str: A conversational response from the LLM.
    """

    if conversation_history is None: 
        conversation_history = []
    
    # 1. Read the prepared text file for LLM grounding.
    try:
        with open(context_file, 'r') as f:
            grounding_data = f.read()
    except FileNotFoundError:
        return "Please upload an AutoCAD DXF file first to provide context for the chatbot."
    except Exception as e:
        return f"An error occurred while reading the context data: {e}"

    # 2. Define the scoring system and instructions for the LLM.
    try:
        with open(PROMPT_TEMPLATE_FILE, 'r') as f:
            unbiased_selection_system = f.read()
    except FileNotFoundError:
        return f"LLM prompt template file not found at {PROMPT_TEMPLATE_FILE}."
    except Exception as e:
        return f"An error occurred while reading the prompt template: {e}"

    # 3. Construct the full prompt for the LLM.
    llm_prompt = f"""
    {unbiased_selection_system}

    ## Provided Context Data:
    {grounding_data}

    ## User Query:
    {user_query}

    Based on your understanding, please respond to the user's query. If a vendor recommendation is requested, follow the specified output format. Otherwise, provide a concise and factual answer.
    """

    messages_input = [
            {"role": "system", "content": llm_prompt},
            *conversation_history,
            {"role": "user", "content": user_query},
        ]

    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages= messages_input,
            temperature=0.5,
            #max_tokens=500
        )
        response = chat_completion.choices[0].message.content.strip()
        return response

    except Exception as e:
        return f"An unexpected error occurred while interacting with the LLM API: {e}. Please try again."
