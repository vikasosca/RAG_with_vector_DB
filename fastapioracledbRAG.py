from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import fitz
from urllib.parse import urlparse
import requests
from google import genai
from google.genai import types
from IPython.display import HTML, Markdown
import oracledb

# Accept url and process:
client = genai.Client(api_key='AIzaSyBlS-ju2iSBZnpcuVDUk2VdI9UKQK4I64U')

#Create a GenerativeModel with the 'gemini-1.5-flash-latest' model
model_id = "gemini-2.5-flash"

# Initialize Oracle connection
def get_db_connection():
    return oracledb.connect(
        user="ADMIN",
        password="Welcome12345",
        dsn="ragai_high",
        config_dir="/content/drive/MyDrive/Colab Notebooks/rag-platform/Wallet_RAGai",
        wallet_location="/content/drive/MyDrive/Colab Notebooks/rag-platform/Wallet_RAGai",
        wallet_password= 'Welcome123',
        ssl_server_dn_match=True   # ensures SSL hostname verification
    )
    
def user_query_embeddings(user_query):

  print(f"user Query: {user_query}")
  embedding = client.models.embed_content(
    model="models/embedding-001",
    contents=user_query
    ).embedding

  dbconn   = None
  dbcursor = None
  
  try:

      dbconn = get_db_connection()
      dbcursor = dbconn.cursor()
      #Run Query
      
      dbcursor.execute("""
        SELECT text
        FROM RAG_CHUNKS
        ORDER BY VECTOR_DISTANCE(embedding, to_vector(:1))
        FETCH FIRST 5 ROWS ONLY
    """, [embedding])

      results = [row[0] for row in dbcursor.fetchall()]
      context = "\n".join(results)
      print("Context: ", results, context)
      return context
  except Exception as e:
      print(f"❌ Error during Embedding Query: {e}")
      return ""
  
def build_RAG_context(new_query:str):
  user_query = new_query
  query_results = user_query_embeddings(user_query)

  context = "\n".join(query_results)
  prompt = f"""
             You are a helpful assistant. Use the following context to answer the question. If you dont find te answer in the context, 
             just say - I dont know. Do not halicunate.
             Context: {query_results} 
             Question: {user_query}
             """  
  response = client.models.generate_content(
    model= model_id,
    contents=prompt
)

  print(f" Response to your query is {response.text}")
  return response.text
            
app = FastAPI()
@app.post("/user_query")

async def user_query(query: str = Form(...)):
    client = genai.Client(api_key='AIzaSyBlS-ju2iSBZnpcuVDUk2VdI9UKQK4I64U')
        
    try:
        processed_response = build_RAG_context(query)
        print(processed_response)
        if processed_response:
           return ("Answer",processed_response)
        else:
           return {"answer": "Sorry, could not find the direct answer"}
       
    except Exception as e:
        print('❌ call to nbuild RAG failed. Please try again.',e)
    
      
