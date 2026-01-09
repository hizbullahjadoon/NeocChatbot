import chromadb
from LLM import get_result
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2
import chunk_with_references
from docx import Document  
import pandas as pd
import io
from tqdm import tqdm

class Chroma:
    def __init__(self, mode):
        self.chroma_client = chromadb.PersistentClient(path="./chroma_local_db")  # Local storage
        self.collection = self.chroma_client.get_or_create_collection(name="disaster_papers_pakistan")
        print("Processed in pakistan mode")
        if mode == "internet":
            self.collection = self.chroma_client.get_or_create_collection(name="disaster_papers_internet")
            print("Processed in internet mode")
        elif mode == "hybrid":
            self.collection = self.chroma_client.get_or_create_collection(name="disaster_papers_hybrid")
            print("Processed in hybrid mode")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
    def extract_references_from_text(self,full_text):
            keywords = ["References", "REFERENCES", "references"]
            start = -1
            for keyword in keywords:
                start = full_text.find(keyword)
                if start != -1:
                    break
            if start != -1:
                return full_text[start:]#.split("\n")
            return ""
    
    def read_pdf(self, file):
        
        reader = PyPDF2.PdfReader(file)
        pages = []
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            pages.append(page.extract_text())
        
        whole_text = " "
        for text in pages:
            whole_text += text
        ref_lines = self.extract_references_from_text(whole_text)
        references = ref_lines
        self.text = whole_text
        return self.text, references
    
    def read_txt(self, file):
        
        file.seek(0)
        raw_data = file.read()

        for encoding in ["utf-8", "latin-1", "windows-1252"]:
            try:
                full_text = raw_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Unable to decode text file.")

        references = self.extract_references_from_text(full_text)
        self.text = full_text
        return self.text, references


    def read_docx(self, file):
        
        doc = Document(file)
        paragraphs = [para.text for para in doc.paragraphs]
        
        # ✅ Join list of paragraphs into a string
        full_text = "\n".join(paragraphs)

        references = self.extract_references_from_text(full_text)  # Now it's a string
        self.text = full_text
        return self.text, references
    
    def convert_to_csv(self, file):
        filename = file.filename
        ext = filename.rsplit('.', 1)[1].lower()

        if ext == 'csv':
            file.seek(0)
            df = pd.read_csv(file)
        elif ext in ['xls', 'xlsx']:
            df = pd.read_excel(file)
        else:
            raise ValueError("Unsupported spreadsheet format")

        # Convert to CSV string (no index column)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        self.text = csv_data
        return self.text, []
        

    def read_files(self):
        self.all_files = []
        self.all_references = []
        for file in self.files:
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext == 'pdf':
                output, references =self.read_pdf(file)
                self.all_files.append(output)
                self.all_references.append(references)

            elif ext == 'txt':
                output, references = self.read_txt(file)
                self.all_files.append(output)
                self.all_references.append(references)  

            elif ext == 'docx':
                output, references = self.read_docx(file)
                self.all_files.append(output)
                self.all_references.append(references)
            elif ext in ['csv', 'xls', 'xlsx']:
                output, references = self.convert_to_csv(file)
                self.all_files.append(output)
                self.all_references.append(references)
            else:
                return "Unsupported file type"
            
        return self.all_files, self.all_references
    
    def insert_docs(self):
        try:
            all_documents, all_references = self.read_files()
            doc_chunks = []

            for i,doc in enumerate(all_documents):
                temp_chunks = self.create_insert_chunks(doc)
                doc_chunks.append(temp_chunks)
            
            all_chunks = chunk_with_references.get_references(doc_chunks, all_references)
            collection = self.chroma_client.get_or_create_collection(name="disaster_papers_hybrid")
            
            for i, doc in tqdm(enumerate(all_chunks)):
                self.embeddings = self.embedding_model.encode(doc["text"]).tolist()
                doc["metadata"]["cited_references"] = {"references":str(doc["metadata"]["cited_references"])}
                
                self.collection.add(
                    ids=[doc["id"]], 
                    documents=[doc["text"]],  
                    embeddings=[self.embeddings],
                    metadatas= [doc["metadata"]["cited_references"]] )

                collection.add(
                    ids=[doc["id"]], 
                    documents=[doc["text"]],  
                    embeddings=[self.embeddings],
                    metadatas= [doc["metadata"]["cited_references"]] )
                
            print("Documents stored successfully in local ChromaDB.")
            
        except Exception as e:
            print("Exception occured: ",e)
        
        
    def create_insert_chunks(self, text):
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", "."]
        )
        chunks = splitter.split_text(text)
        
        return chunks
    
    def create_chunks(self, text):
        r_splitter = RecursiveCharacterTextSplitter(
            separators= ["\n\n", "\n", "."],
            chunk_size = 1200,
            chunk_overlap = 150
        )
        chunks = r_splitter.split_text(text)

        return chunks
    
    def count_tokens(self,text):
        return len(text.split())  # Rough token estimate

    def search_documents(self, query):
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(query_embeddings=[query_embedding], n_results=10)
        self.retrieved_docs = results["documents"]
        metadatas = results["metadatas"]
        full_context = results["documents"]
        self.context = full_context
        return self.context, metadatas
    
    def call_llm(self,context1, query, recent_history, ref):
        extract_result = get_result().extract_result(text = context1, query=query, recent_history= recent_history, references_for_each_chunk=ref)
        return extract_result
