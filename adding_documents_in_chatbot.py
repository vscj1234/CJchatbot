# -*- coding: utf-8 -*-
"""adding documents in chatbot.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/132fu11H5am5l3Ng4GfyGIx_o69G_qTuS
"""

# Install necessary libraries
!pip install langchain openai python-dotenv
!pip install "unstructured[md]" onnxruntime
!pip install langchain-community
!pip install -U langchain-openai
!pip install chromadb
!pip install pymupdf

import os
import fitz #PyMuPDF
# Set your OpenAI API key
os.environ['OPENAI_API_KEY'] = ' '

from google.colab import files
import os
import shutil
# Set the directory where you'll store your data
DATA_PATH = "/home"

# Create the directory if it doesn't exist
os.makedirs(DATA_PATH, exist_ok=True)

# Upload files
uploaded = files.upload()

# Move uploaded files to the data directory
for filename in uploaded.keys():
    shutil.move(filename, os.path.join(DATA_PATH, filename))

from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
import os
import shutil
import fitz  # PyMuPDF

CHROMA_PATH = "/content/chroma_db"  # Use a writable directory


def get_embedding_function():
    """Return an OpenAI embedding function."""
    return OpenAIEmbeddings()

def main():
    generate_data_store()

def generate_data_store():
    documents = load_documents()
    if not documents:
        print("No documents found. Exiting.")
        return
    chunks = split_text(documents)
    if not chunks:
        print("No chunks generated. Exiting.")
        return
    save_to_chroma(chunks)

def load_documents():
    # Load PDF documents from the directory
    documents = []
    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".pdf"):
            filepath = os.path.join(DATA_PATH, filename)
            with fitz.open(filepath) as doc:
                for page_number, page in enumerate(doc, start=1):
                    text = page.get_text()
                    # Create Document object
                    document = Document(page_content=text, metadata={"source": filepath, "page": page_number})
                    documents.append(document)
    print(f"Loaded {len(documents)} documents.")
    return documents

def split_text(documents):
    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,  # Increase chunk size for more content
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

# Add unique ID to each chunk
    chunk_id_counter = {}
    for chunk in chunks:
        source = chunk.metadata.get('source', 'unknown')
        page_number = chunk.metadata.get('page', 0)
        if (source, page_number) not in chunk_id_counter:
            chunk_id_counter[(source, page_number)] = 0
        chunk_index = chunk_id_counter[(source, page_number)]
        chunk.metadata['id'] = f"{source}-page{page_number}-chunk{chunk_index}"
        chunk_id_counter[(source, page_number)] += 1

    return chunks

def save_to_chroma(chunks):
    # Initialize Chroma database
    db = Chroma(embedding_function=get_embedding_function(), persist_directory=CHROMA_PATH)

    # Add or update chunks in the database
    for chunk in chunks:
        chunk_id = chunk.metadata['id']
      # Perform a search to check for existence
        search_results = db.similarity_search(chunk_id, k=1)

        if not search_results:
            # Add new chunk if not found
            db.add_documents([chunk], ids=[chunk_id])
            print(f"Added chunk {chunk_id}")
        else:
            # Assuming we can only add and can't truly update; add again
            db.add_documents([chunk], ids=[chunk_id])
            print(f"Updated chunk {chunk_id}")

    db.persist()
    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")

if __name__ == "__main__":
    main()

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate


# Define the prompt template
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

def query_database(query_text):
    # Prepare the DB
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB
    results = db.similarity_search_with_relevance_scores(query_text, k=5)
    if len(results) == 0 or results[0][1] < 0.7:
        print("Unable to find matching results.")
        return

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    model = ChatOpenAI()
    response_text = model.predict(prompt)

    sources = [doc.metadata.get("source", None) for doc, _ in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)

# Example query
query_text = "What services do you offer?"
query_database(query_text)

# Example query
query_text = "Who is the founder and CEO of CloudJune?"
query_database(query_text)

