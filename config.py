import os
from dotenv import load_dotenv

# 1. Load the hidden variables into the environment
load_dotenv()

# 2. Retrieve the specific token
BOT_TOKEN = os.getenv("BOT_TOKEN")