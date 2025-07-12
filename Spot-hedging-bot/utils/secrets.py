from dotenv import load_dotenv # type: ignore
import os

load_dotenv()
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET = os.getenv("OKX_SECRET")
