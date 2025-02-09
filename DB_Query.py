import re
import os
import pandas as pd
import sqlite3
import json
from dotenv import load_dotenv
from openai import OpenAI
import io
import matplotlib as plt
import base64

class Q:
    def __init__(self,df,model = "gpt-4o", company=True):
        self.df = df
        self.schema = self.generate_schema() 
        self.model=model
        self.db = "data.db"
        self.conn = sqlite3.connect(self.db)
        self.cursor = self.conn.cursor()
        self.df.to_sql('purchase', self.conn, if_exists='replace', index=False)
        
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)
        
        if company:
            self.system_prompt = "\
            You are a SQL expert. Given the following schema and valid categorical values, generate a SQL query to answer the user's question. The table name is purchase\
            Do your best to interpret the user's request if there are spelling issues or inconsistencies with a user defined category and one in the Schema.\
            Return a table that displays both the labels and values and the value.\
            Do not filter a column to a value that isn't in the schema, find the closest match using LIKE in the query.\
            Calculations involving measurements such as spend must include a multiplication with gweight in order to represent total population figures.\
            Buyers are distinct buyer IDs, they similarly should be multiplied by Gweight.\
            When asked for YOY growth use percentages.\
            Return only the SQL code in a form I can execute it without modification. It must run in sqllite."
            
        else:
            self.system_prompt = "\
            You are a SQL expert. Given the following schema and valid categorical values, generate a SQL query to answer the user's question. The table name is purchase\
            Do your best to interpret the user's request if there are spelling issues or inconsistencies with a user defined category and one in the Schema.\
            Return a table that displays both the labels and values and the value.\
            Do not filter a column to a value that isn't in the schema, find the closest match using LIKE in the query.\
            Return only the SQL code in a form I can execute it without modification. It must run in sqllite."
            
        self.system_prompt2= "\
            You are a data analyst.Use the following data in json format, combined to answer the user prompt that follows.\
            If the data can be plotted, generate matplotlib code along with a text response.\
            If you are only answering about 1 value do not generate python code.\
            Use as little text and code needed to answer the question.\
            Only return one piece of text and one code block. Do not announce the codeblock.\
            Spend is in £, volume is in KG. Format the output and plot to maximise readability for the user.\
            Convert these values to or Millions when plotting if neccessary to avoid 1e6 appearing on the plot\
            "

    def generate_schema(self):
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
            
        for col in self.df.columns:
            if self.df[col].dtype == 'object':  
                try:
                    self.df[col] = pd.to_numeric(self.df[col])
                except ValueError:
                    pass  
        
        self.schema = {'columns': {}}
        for column in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df[column]):
                self.schema['columns'][column] = {'type': 'numeric'}
            elif pd.api.types.is_object_dtype(self.df[column]) or isinstance(self.df[column].dtype, pd.CategoricalDtype):
                self.schema['columns'][column] = {'type': 'categorical', 'values': self.df[column].dropna().unique().tolist()}
            elif pd.api.types.is_datetime64_any_dtype(self.df[column]):
                self.schema['columns'][column] = {'type': 'datetime'}
            else:
                self.schema['columns'][column] = {'type': 'unknown'}
        return self.schema
                
    def generate_SQL(self,user_prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt}, 
                {"role": "system", "content": json.dumps(self.schema)},
                {"role": "user", "content": user_prompt},
                ],
            max_tokens=500,
            temperature=0.7
        ).choices[0].message.content
        return self.strip_SQL(response)
    
    def strip_SQL(self,response):
        pattern = r"```sql(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        return match.group(1)
        
    def execute_SQL(self,SQL):
        try:
            self.cursor.execute(SQL)
            result = self.cursor.fetchall()
            json_data = [{"Name": row[0], "Value": row[1]} for row in result]
            json_string = json.dumps(json_data, indent=2)
            return json_string
        except:
            return None

    def generate_response(self, user_prompt, response):
        system_prompt = self.system_prompt2
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "system", "content": response},
                {"role": "user", "content": user_prompt},
                ],
            max_tokens=500,
            temperature=0.7
        ).choices[0].message.content
        
        return self.strip_python(response)
    
    def strip_python(self,response, history):
        pattern = r"```python(.*?)```"
        py_code = re.findall(pattern, response, re.DOTALL)
        
        if not py_code:
            return None, response
        
        py_code = py_code[0].strip().replace("\\'", "'")
        text = re.sub(pattern, '', response, flags=re.DOTALL).strip()
        if text == '':
            return py_code, None
        return py_code, text
    
    def execute_python(self, py):
        try:
            exec(py, globals())
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)  
            img_bytes = buf.getvalue()
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
            
    def ask_diallo(self,prompt):
        SQL = self.generate_SQL(prompt)
        result = self.execute_SQL(SQL)
        if not result:
            return None,None
        
        py,text = self.generate_response(prompt, result)
        if py:
           return text, self.execute_python(py)
        return text, None