import os
import json
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

class GoogleSheetManager:
    def __init__(self):
        # 1. Load the JSON string from the environment and parse it back into a dictionary
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        
        if not creds_json or not self.spreadsheet_id:
            raise ValueError("Missing Google Credentials in .env")

        creds_dict = json.loads(creds_json)
        
        # 2. Define the cryptographic scope (what this bot is allowed to do)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 3. Authenticate and create the client
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        self.client = gspread.authorize(credentials)

    def upload_dataframe(self, df: pd.DataFrame):
        """Wipes the target Google Sheet and uploads the new Pandas DataFrame."""
        # 1. Connect to the specific Google Sheet and grab the first tab (Sheet1)
        sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
        
        # 2. Wipe the existing data completely clean
        sheet.clear()

        # 3. Defensive Check: If DataFrame is empty, stop here.
        if df.empty:
            return

        # 4. Data Conversion: Fill NaNs with 0, and convert all data to standard Python types
        df = df.fillna(0)
        # YOUR ENGINEERING TASK: 
        # Convert the DataFrame headers into a list. Example: [df.columns.values.tolist()]
        # Convert the DataFrame rows into a list of lists. Example: df.values.tolist()
        # Concatenate them together so the headers sit on top of the rows.
        headers = df.columns.values.tolist()
        rows = df.values.tolist()

        matrix = [headers] + rows
        
        # 5. Execute the massive batch API update
        # Syntax: sheet.update(values=your_concatenated_list, range_name='A1')
        sheet.update(values=matrix, range_name = 'A1')