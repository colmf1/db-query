import re
import pandas as pd
import psycopg2
import sqlalchemy as sa
import json
import io
import os
import base64
import matplotlib.pyplot as plt
import logging
#from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import StrOutputParser
from langchain_community.document_loaders import TextLoader, DirectoryLoader  
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma  
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

class Q:
    def __init__(self, df, model="gpt-4o-mini"):
        self.setup_logging()
        self.df = df
        self.schema = self.generate_schema()
        #self.logger.info(f"\Schema: \n{json.dumps(self.schema)}")  
        self.model = model
        
        #load_dotenv()  
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.db_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "postgres"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres"),
            "port": os.getenv("DB_PORT", "5432")
        }
        
        self.engine = sa.create_engine(
            f"postgresql://{self.db_params['user']}:{self.db_params['password']}@"
            f"{self.db_params['host']}:{self.db_params['port']}/{self.db_params['database']}"
        )
        
        try:
            self.df.to_sql('purchase', self.engine, if_exists='replace', index=False)
        except Exception as e:
            self.logger.error(f"Error uploading dataframe to PostgreSQL: {e}")
            raise
        
        self.conn = psycopg2.connect(**self.db_params)
        self.cursor = self.conn.cursor()
        
        self.sql_llm = ChatOpenAI(model=model, temperature=0.2, openai_api_key=api_key)
        self.response_llm = ChatOpenAI(model=model, temperature=0.5, openai_api_key=api_key)
        self.setup_vectorstores()
        self.setup_chains()
    
    def setup_logging(self):
        self.logger = logging.getLogger('QChatbot')
        self.logger.setLevel(logging.DEBUG)
        
        file_handler = logging.FileHandler('qchatbot.log')
        file_handler.setLevel(logging.DEBUG)
        
        #console_handler = logging.StreamHandler()
        #console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        #console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        #self.logger.addHandler(console_handler)
        
    def setup_vectorstores(self):         
        self.embeddings = OpenAIEmbeddings()                  
        sql_loader = DirectoryLoader("sql_docs", glob="*.txt", loader_cls=TextLoader)         
        sql_docs = sql_loader.load()                  
        text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=400)
        sql_splits = text_splitter.split_documents(sql_docs)                  
        self.sql_vectorstore = Chroma.from_documents(documents=sql_splits,embedding=self.embeddings,collection_name="sql_instructions_pg",persist_directory="./chroma_pg_db")                  
        self.sql_retriever = self.sql_vectorstore.as_retriever(search_kwargs={"k": 2})                  
        #compressor = LLMChainExtractor.from_llm(self.sql_llm)         
        #self.sql_retriever = ContextualCompressionRetriever(base_compressor=compressor,base_retriever=self.sql_retriever)

    def setup_chains(self):
        sql_system_prompt = """
            "You are an expert SQL assistant designed to write SQL queries for PostgreSQL databases. I will provide you with context and a database schema and your task is to generate SQL code based on my requests. Follow these rules strictly:
            Only write SQL queries (e.g., SELECT statements) and avoid any operations that modify data, such as INSERT, UPDATE, or DELETE.
            Do not add or remove any lines from the schema or tables; work only with the provided schema as-is.
            When filtering data (e.g., in WHERE clauses), only use column names and values that exist in the provided schema. 
            Do not invent column names, values, or tables not explicitly mentioned. Only use dates within the date range.
            Ensure all SQL code is valid and executable in PostgreSQL.
            If the request is unclear or the schema lacks necessary information, ask for clarification.
            Spend, Volume and Pack figures must be multiplied by a weight column.
            Provide the SQL code in a code block with no explanation. The table name is purchase.
            The user can compare measures(eg.spend,volume,packs) and categories(brand,store,market) over time periods from the date column.
            If no measure is specified, use spend, if no time period is specified use the latest year from the date_range: max in the schema.
            """
            
        sql_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(sql_system_prompt),
            SystemMessagePromptTemplate.from_template("Use the following context to help: {context}"),
            SystemMessagePromptTemplate.from_template("The database schema is: {schema}"),
            HumanMessagePromptTemplate.from_template("{question}")
        ]) 
        
        self.sql_chain = sql_template | self.sql_llm | StrOutputParser() | self.strip_SQL
        
        analysis_system_prompt = """
            You are a Data Consultant working with a Data Analyst. You will recieve SQL Code, the output data of that SQL query in json format,
            and use it to answer the users question. You must decide how to use the data to answer the users question. Use the SQL code to determine data labels.
            Generate matplotlib code to display the data if helpful. When labelling data, Spend is in £ and Volume is in KG, growth/decline will be in %.
            Format the output and the plot to provide maximum readability to the user. If data is in large numbers convert to thousands or millions, round to 3dp and use labels.
            Mention the time period or any rolling aggregation used by the SQL code in the response so the user understands what they're seeing, and ensure it's labelled on any graph produced.
            Return only one piece of text, one code block, or both. Do not announce the code block."""
            
        response_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(analysis_system_prompt),
            SystemMessagePromptTemplate.from_template("SQL Query: {sql}"),
            SystemMessagePromptTemplate.from_template("Data: {data}"),
            HumanMessagePromptTemplate.from_template("{question}")
        ])
        self.response_chain = response_template | self.response_llm | StrOutputParser()

    def strip_SQL(self,response):
        pattern = r"```sql(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        out = match.group(1).replace("\nLIMIT 1", "\nLIMIT 5").replace("DELETE|INSERT","")
        return out.strip()

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
                min_date = self.df[column].min().strftime('%Y-%m-%d')
                max_date = self.df[column].max().strftime('%Y-%m-%d')
                self.schema['columns'][column] = {'type': 'datetime', 'date_range': {'min': min_date, 'max': max_date}}
            else:
                self.schema['columns'][column] = {'type': 'unknown'}
        
        return self.schema
                
    def generate_SQL(self, user_prompt):
        try:
            docs = self.sql_retriever.invoke(user_prompt)
            context = "\n".join([doc.page_content for doc in docs])
            self.logger.info(f"User Prompt: \n{user_prompt}")
            self.logger.info(f"Docs: \n{docs}")

            SQL_out = self.sql_chain.invoke({
                "context": context,
                "schema": json.dumps(self.schema),
                "question": user_prompt
            })
                      
            self.logger.info(f"SQL Code:\n{SQL_out}\n")
            return SQL_out
        except Exception as e:
            self.logger.error(f"Error generating SQL: {e}")
            return None
    
    def execute_SQL(self, SQL):
        try:
            self.cursor.execute(SQL)
            result = self.cursor.fetchall()
            column_names = [desc[0] for desc in self.cursor.description]
            
            json_data = []
            for row in result:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[column_names[i]] = value
                json_data.append(row_dict)
                
            data = json.dumps(json_data, indent=2, default=str) 
            self.logger.info(f"Data Extracted: {data}")
            return data
        except Exception as e:
            self.logger.error(f"SQL execution error: {e}")
            self.conn.rollback()
            return None

    def generate_response(self, user_prompt, response_data, SQL):
        try:
            response = self.response_chain.invoke({
                "sql": SQL,
                "data": response_data,
                "question": user_prompt
            })            
            return self.split_python(response)
        except Exception as e:
            self.logger.error(f"Error generating Analysis response: {e}")
            return None, None
    
    def split_python(self, response):
        pattern = r"```python(.*?)```"
        py_code = re.findall(pattern, response, re.DOTALL)

        if not py_code:
            self.logger.info(f"Extracted text: {response}")
            self.logger.info("No Python code found in response")
            return response, None
        
        py_code = py_code[0].strip().replace("\\'", "'")
        text = re.sub(pattern, '', response, flags=re.DOTALL).strip()

        self.logger.info(f"Extracted text: {text}")
        self.logger.info(f"Extracted Python code: {py_code}")
        if text == '':
            return None, py_code
        return text, py_code
    
    def execute_python(self, py):
        try:
            exec_globals = {
                'plt': plt,
                'pd': pd,
                'json': json,
                'io': io,
                'base64': base64
            }
            
            exec(py, exec_globals)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)  
            img_bytes = buf.getvalue()
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Python execution error: {e}")
            return None
            
    def ask_Q(self, prompt):
        SQL = self.generate_SQL(prompt)
        if not SQL:
            return "I wasn't able to fetch the data you requested, please provide more information", None
        
        result = self.execute_SQL(SQL)
        if not result:
            return "I wasn't able to use the fetched data to answer your question. Sorry", None
        
        text, py = self.generate_response(prompt, result, SQL) 
        if py:
            img = self.execute_python(py)
            return text, img
        return text, None
    
    def __del__(self):
        try:
            self.sql_vectorstore.delete_collection()
        except Exception as e:
            print(f"Error while deleting vector store: {e}")

        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()