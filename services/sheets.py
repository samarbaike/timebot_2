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

    def _get_or_create_sheet(self, spreadsheet, title: str):
        try:
            return spreadsheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=title, rows=200, cols=50)

    def _build_pivot(self, df, pivot_column: str):
        pivot = df.pivot_table(
            index='full_name',
            columns=pivot_column,
            values='pages_read',
            aggfunc='sum',
            fill_value=0
        )
        pivot.insert(0, 'Total', pivot.sum(axis=1))
        pivot = pivot.sort_values('Total', ascending=False)
        return pivot.reset_index().rename(columns={'full_name': 'Name Surname'})

    def _write_to_sheet(self, worksheet, df):
        worksheet.clear()
        headers = df.columns.values.tolist()
        rows = df.values.tolist()
        worksheet.update(values=[headers] + rows, range_name='A1')

    def upload_both_tabs(self, df):
        spreadsheet = self.client.open_by_key(self.spreadsheet_id)

    # --- Tab 1: daily progress ---
        df['log_date'] = df['log_date'].apply(
            lambda d: d.strftime('%b %d') if hasattr(d, 'strftime') else d
        )
        daily_df = self._build_pivot(df, pivot_column='log_date')
    
    # Reverse date columns so newest is leftmost (keep Name Surname and Total fixed)
        fixed_cols = ['Name Surname', 'Total']
        date_cols = [c for c in daily_df.columns if c not in fixed_cols]
        daily_df = daily_df[fixed_cols + date_cols[::-1]]

        daily_sheet = self._get_or_create_sheet(spreadsheet, '📊 Progress')
        self._write_to_sheet(daily_sheet, daily_df)

    # --- Tab 2: books ---
        books_df = self._build_pivot(df, pivot_column='title')
        books_sheet = self._get_or_create_sheet(spreadsheet, '📚 Kitepter')
        self._write_to_sheet(books_sheet, books_df)