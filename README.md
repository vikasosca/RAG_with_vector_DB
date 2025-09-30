RAG-Based Research Search System with Oracle vector database

A cutting-edge solution to efficiently search through academic research papers downloaded from Arxiv, using Retrieval-Augmented Generation (RAG) and Oracle 23AI for lightning-fast, context-aware search results.

Table of Contents

Introduction

Tech Stack

Features

Setup and Installation

Usage

How It Works

License

Introduction

This project is designed to solve the information overload problem faced by researchers, engineers, and students when trying to search through large volumes of academic papers. By leveraging modern NLP techniques and Oracle 23AI Vector Database, the system can intelligently extract, chunk, and store research paper contents for rapid, context-aware querying.

No more wading through pages of research! With this system, you can ask specific, semantically rich questions and get accurate results instantly.

Tech Stack 🛠️

Python 3.x

FastAPI: For building the RESTful API service to interact with the database.

Oracle 23AI Vector Database: Scalable, high-performance vector search engine that understands semantic relationships within your data, allowing for context-based search results.

NLP (Natural Language Processing): For intelligent query interpretation and chunking of PDF documents.

PDF Parsing: Libraries to extract text from PDF files.

Features 🌟

Arxiv PDF Downloader: Automatically fetches PDFs on a specific topic from Arxiv.

PDF Chunking: Breaks down the content into smaller, meaningful chunks for easier querying.

Semantic Search with Oracle 23AI: Stores text chunks in a vector database, enabling context-aware search capabilities.

Fast API Interface: Search your research collection through a fast and intuitive API.

Efficient: Lightning-fast search results, even when dealing with thousands of academic papers.

Setup and Installation 🏗️
Prerequisites

Before running the application, ensure that you have the following:

Python 3.7+ installed.

An Oracle 23AI account and access to their vector database.

An Arxiv account for downloading PDFs (optional, depending on access method).

Basic knowledge of FastAPI to set up and run the service.

Install Dependencies

Clone the repository:

git clone https://github.com/your-username/rag-research-search.git
cd rag-research-search


Create a virtual environment and install dependencies:

python3 -m venv venv
source venv/bin/activate  # On Windows, use 'venv\Scripts\activate'
pip install -r requirements.txt


Set up Oracle 23AI Vector Database and configure connection details in the config.py file.

Usage 🔍

Once the setup is complete, you can start interacting with the application:

Download PDFs from Arxiv:

You can specify a topic or research query, and the system will download related PDFs from Arxiv:

python download_pdfs.py --topic "Quantum Computing"


Chunk the PDFs and Upload to Oracle 23AI:

Once PDFs are downloaded, the next step is to chunk them into smaller pieces and load them into the Oracle 23AI database:

python chunk_and_upload.py --pdf_folder ./downloads


Start FastAPI Server:

Run the FastAPI server to interact with your data:

uvicorn main:app --reload


Search for Information:

Use the API to query your research papers. For example, to search for a specific concept or phrase:

curl -X 'POST' \
  'http://127.0.0.1:8000/search' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "What is the latest algorithm for quantum error correction?"
}'

How It Works 🧠

PDF Downloader: The system fetches PDF files related to a specific topic from Arxiv.

Chunking Process: Each PDF is split into smaller semantic chunks, where each chunk is stored as an individual unit in the database.

Vector Search: Using Oracle 23AI's vector database, each chunk is transformed into a vector representation, capturing both the meaning and context of the text. This allows for more intelligent, context-aware searching than simple keyword-based queries.

Fast Search via FastAPI: The FastAPI interface provides an intuitive way to query the database using natural language prompts, and the system will return highly relevant search results in near-instant time.
