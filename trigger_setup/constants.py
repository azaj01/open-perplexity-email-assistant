from composio import Composio
from langchain_openai import ChatOpenAI
import os

from dotenv import load_dotenv

load_dotenv()

def initialise_composio_client():
    return Composio(api_key=os.getenv("COMPOSIO_API_KEY"))

def initialise_chatmodel():
    return ChatOpenAI(model="gpt-5", api_key=os.getenv("OPENAI_API_KEY"))