# Install following files
import re
import arxiv # This is the source of research papers
from pathlib import Path
import os
import json
from google.colab import drive
from unstructured.partition.pdf import partition_pdf
from sentence_transformers import SentenceTransformer
from IPython.display import HTML, Markdown
from datetime import datetime
import time
import oracledb
from logging import exception
from huggingface_hub import login

# Define a print methid which captures time
def tprint(*args,**kwargs):
  start =  time.time()
  dt = datetime.fromtimestamp(start)
# Format to dd-mon-yyyy mi:hh:ss
  formatted_time = dt.strftime("%d-%b-%Y %M:%H:%S")

  print(formatted_time,"-",*args)
  return

"""#Get Database Connections"""

# Initialize Oracle connection
def get_db_connection():
    return oracledb.connect(
        user="******",
        password="**********",
        dsn="ragai_high",
        config_dir="/content/drive/MyDrive/Colab Notebooks/rag-platform/Wallet_RAGai",
        wallet_location="/content/drive/MyDrive/Colab Notebooks/rag-platform/Wallet_RAGai",
        wallet_password= '*******',
        ssl_server_dn_match=True   # ensures SSL hostname verification
    )

"""#Initialize Variables"""
def init_var():

	max_batch_size = 7 # Change this value as per the availability of CPU
	# Accept url and process:
	download_files = True
	start =  time.time()
	output_dir = Path("/content/drive/MyDrive/Colab Notebooks/rag-platform")
	output_dir.mkdir(exist_ok=True)

	METADATA_FILE = output_dir / 'papers.json'
	CHUNKS_FILE = output_dir / 'chunks.json'
	temp_data = True

	try:
	  model = SentenceTransformer('all-MiniLM-L6-v2')
	except Exception as e:
	  print(f"Error in loading model: {e}")
	  raise

	embeddings = None
	processed_ids = set()  # keep track of already processed PDFs
	papers_to_process = []
	valid_papers = []

	# Load or initialize file
	if os.path.exists(METADATA_FILE):

	    with open(METADATA_FILE, 'r') as f:
		processed_papers = json.load(f)
		tprint('Meatdata file path exists',processed_papers)
	else:
	    processed_papers = []

	processed_ids = {p['paper_id'] for p in processed_papers}
	print(f"✅ Loaded {len(processed_ids)} already processed papers.")


"""#Sanitize the data"""

def sanitize_metadata(meta: dict) -> dict:
    safe_meta = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe_meta[k] = v
        else:
            # For lists, dicts, etc. → store as JSON string
            safe_meta[k] = json.dumps(v)
    return safe_meta

"""#Delete loaded files"""

import contextlib

with contextlib.suppress(FileNotFoundError):
    os.remove(output_dir / 'chunks.json')

for filename in os.listdir(output_dir):
        # Check if the file is a PDF (ends with .pdf)
        if filename.lower().endswith('.pdf'):
            # Construct the full file path
            file_path = os.path.join(output_dir, filename)
            try:
                # Delete the PDF file
                os.remove(file_path)
                print(f"Deleted: {filename}")
            except Exception as e:
                print(f"Error deleting {filename}: {e}")

"""#Setup the client"""

client = arxiv.Client(
    delay_seconds = 3 )

# Search for paperson the website for a keyword

search = arxiv.Search(query = "Artificial Intelligence",
                      max_results=max_batch_size,
                      sort_by=arxiv.SortCriterion.SubmittedDate )


papers = []
papers_meta = []
for pdf_files in output_dir.glob("arxiv*.pdf"):
  download_files = False
  paper_id_match = re.search(r"arxiv_(.*?)\.pdf", pdf_files.name)
  if not paper_id_match:
    continue
  paper_id = paper_id_match.group(1)
  if paper_id in processed_ids:
    continue

  papers_meta ={
            "Title": pdf_files.stem,
            "author": [],
            "abstract": "",
            "paper_id": paper_id,
            "filename": pdf_files.name
         }
  papers.append(papers_meta)
  papers_to_process.append((pdf_files, papers_meta))

if download_files:
  tprint(" Starting downloading files.. ")
  papers = []
  for i, paper in enumerate(client.results(search)):
      tprint(f"Paper processed: {i} - {paper}")
      paper_id = paper.get_short_id()
      if paper_id in processed_ids: # Do not reprocess the file
        continue
      try:
        filename = f"arxiv_{paper_id}.pdf"

        paper.download_pdf(dirpath=output_dir, filename=filename)

        papers.append (
            {
            "Title": paper.title,
            "author": [str(a) for a in paper.authors],
            "abstract": paper.summary,
            "paper_id": paper.entry_id,
            "filename": filename
        })
        processed_ids.add(paper_id)

        # Save metadata for insertion into ChromaDB as vector embeddings

        if (i+1)%10 == 0:
          tprint("=========>>> Output dir:", output_dir,len(papers))
          with open(METADATA_FILE, 'w') as f:
            json.dump(papers, f, indent=2)

      except Exception as e:
        tprint(f"Exception raised during paper download - {e}")
        continue

"""#Parse pdf files"""

def parse_files(valid_papers):

  try:
    for paper in valid_papers:
        try:

            tprint('Parsing files - ', paper)
            if "doc_id" not in paper:
              continue
            pdf_path = output_dir / paper["filename"]

            elements = partition_pdf(str(pdf_path), strategy="auto",languages=["en"], pdf_extract_image=True, ) #Auto uses best strategy for parsing

            full_text = "\n".join(str(e) for e in elements)
            paper_meta = paper
            chunks = [] # Initialize per document

            for i, e1 in enumerate(elements):
              tprint(f' i : {e1}')
              chunk = {"text": str(e1), "AIresearchpapers": sanitize_metadata(paper_meta),  "chunk_index": i}
              if "doc_id" not in chunk["AIresearchpapers"]:
                  tprint(f"Missing doc_id in chunk for paper {paper['paper_id']}: {chunk['AIresearchpapers']}")
                  continue
              chunks.append(chunk)

              # This file contains the parsed chunks extracted from those papers' PDFs.
              # Dont need the below segment as we are inserting in OCI 23ai db but leaving it there for we dont know when it would be needed
            #tprint("Chunk File is: ", chunks)
        except Exception as e:
          tprint(f"Error parsing {paper['filename']}: {e}")
          continue

    with open(CHUNKS_FILE, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")  # One chunk per line
  except Exception as e:
    tprint(f"Error occuring during parsing files: {e}")

"""#Embed Chunks: Use Sentence Transformers to generate embedding"""

def embed_chunks():

  global embeddings
  temp_chunks = []
  full_chunks = []
  try:
    with open(CHUNKS_FILE, 'r') as f:
        for line in f:
          if line.strip():  # skip empty lines
            temp_chunks.append(json.loads(line))

    full_chunks =  temp_chunks
    tprint("Full Chunks: ", full_chunks)
    documents = [chunk["text"] for chunk in full_chunks]

    if documents:
      embeddings = model.encode(documents, show_progress_bar=True)
      tprint("Embeddings generated:", type(embeddings), embeddings.shape)
    else:
      tprint("No chunks to encode, embeddings remain None")
      raise ValueError("No documents to encode")

    return full_chunks, embeddings

  except Exception as e:
    print(f"Error in embedding chunks: {e}")
    raise

"""#Save into 23ai OCI Autonomoous Vector database"""
def main():

def init_var() # call init function

# Insert data into OCI 23AI
myconn = None
ocicursor = None
try:

    myconn = get_db_connection()
    ocicursor = myconn.cursor()
    # Insert into documents table
    doc_id_var = ocicursor.var(int)
    for paper in papers:
        print('Inserting into Documents Table: ')
        ocicursor.execute("""
                    INSERT INTO documents (title, authors, abstract, paper_id, filename)
                    VALUES (:1, :2, :3, :4, :5)
                    RETURNING doc_id INTO :6
                            """, (
                                paper["Title"],
                                json.dumps(paper["author"]),
                                paper["abstract"],
                                paper["paper_id"],
                                paper["filename"],
                                doc_id_var
                            ))
        paper["doc_id"] = doc_id_var.getvalue()[0]  # Store doc_id for chunks
        valid_papers.append(paper)
        # Insert into chunks table

        parse_files(valid_papers) #Parse files
        full_chunks, embeddings = embed_chunks() #embed chunks

        for chunk, embedding in zip(full_chunks, embeddings):
                if "AIresearchpapers" not in chunk:
                    tprint(f"Chunk missing 'AIresearchpapers' key!", chunk)
                    continue
                if "doc_id" not in chunk["AIresearchpapers"]:
                    tprint(f"Missing doc_id in chunk for paper {chunk['AIresearchpapers'].get('paper_id', 'unknown')}: {chunk['AIresearchpapers']}")
                    continue

                doc_id = chunk["AIresearchpapers"]["doc_id"]
                ocicursor.execute("""
                    INSERT INTO RAG_CHUNKS (doc_id, text, embedding)
                    VALUES (:1, :2, TO_VECTOR(:3) )
                """, (doc_id, chunk["text"], json.dumps(embedding.tolist())))  # Convert embedding to list
                myconn.commit()

except oracledb.Error as e:
                print(f"Error occured during Oracle connections - {e}")
except Exception as e:
              print(f" Unknown Error occured while loading data - {e}")
finally:
         if ocicursor:
             ocicursor.close()
         if myconn:
             myconn.close()
