import requests
from PyPDF2 import PdfReader
import io

from dotenv import load_dotenv
import os
from openai import OpenAI



load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def download_pdf_from_s3(s3_url):
    print("📥 Downloading PDF from S3...")
    response = requests.get(s3_url)
    response.raise_for_status()
    return io.BytesIO(response.content)

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n\n"
    return text

s3_url = "https://my-mapbox-data-geojson.s3.us-east-2.amazonaws.com/BBB_HR1.pdf"
pdf_file = download_pdf_from_s3(s3_url)
full_text = extract_text_from_pdf(pdf_file)

def chunk_text(text, max_chunk_length=3000):
    """
    Splits the input text into manageable chunks based on paragraphs,
    staying within a maximum character limit per chunk.
    """
    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chunk_length:
            current_chunk += para + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
MAX_CHUNKS = 10
chunks = chunk_text(full_text)
chunks = chunks[:MAX_CHUNKS]
print(f"✅ Split into {len(chunks)} chunks.")

def summarize_chunk(client, chunk):
    prompt = f"""
You are a policy analyst focused on nuclear energy. Read the following legislative text chunk and summarize it in plain English in seven pages. 

- Highlight only the parts relevant to nuclear energy, including supply chains, manufacturing, power generation, tax credits, or references to clean energy programs.
- If the section is not relevant to nuclear energy, say: 'No nuclear-related content in this section.'
- Be concise and accurate.
- each section is written as "sec. #####" or something similar. if there is legislation that is pertinent to nuclear, make sure to reference the particular section it is in.
- if there are changes, be very specific about numbers. if a tax credit is changed from 10% to 20%, say that explicitly. or if the year is changed, say that expictly. 
- if a law is updated or rescinded, say what that previous law was and what the new law is.
--- Start of text chunk ---
{chunk}
--- End of text chunk ---
"""
    response = client.chat.completions.create(
        model="gpt-4-turbo", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("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"))

summaries = []
for i, chunk in enumerate(chunks):
    print(f"✏️ Summarizing chunk {i+1}/{len(chunks)}...")
    summary = summarize_chunk(client, chunk)
    summaries.append(summary)


import re

def extract_references(text):
    patterns = [
        r"(Section\s\d{3,5}.*?Public Law \d{3}-\d{3})",  # e.g., Section 13704 of Public Law 117-169
        r"(CFR\s?\d{1,3}\s?(Part|§)?\s?\d+)",            # e.g., CFR 10 Part 50
        r"Section\s\d+[A-Z]?",                           # e.g., Section 45X
    ]
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text))
    return [m if isinstance(m, str) else m[0] for m in matches]


from serpapi import GoogleSearch
import os

def search_reference_with_serpapi(query):
    params = {
        "engine": "google",
        "q": query,
        "api_key": os.getenv("SERPAPI_API_KEY")
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    
    snippets = []
    if "organic_results" in results:
        for result in results["organic_results"][:3]:
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            snippets.append(f"{snippet} [source: {link}]")
    
    return "\n".join(snippets) if snippets else "No relevant information found."


for i, chunk in enumerate(chunks):
    print(f"✏️ Summarizing chunk {i+1}/{len(chunks)}...")

    refs = extract_references(chunk)
    extra_context = ""

    for ref in refs:
        print(f"🔎 Looking up: {ref}")
        search_result = search_reference_with_serpapi(ref)
        extra_context += f"\nContext for {ref}:\n{search_result}\n"

    summary = summarize_chunk(client, chunk + "\n\n" + extra_context)
    summaries.append(summary)

def summarize_chunk_with_context(client, chunk_text, external_context):
    prompt = f"""
You are a policy analyst focused on nuclear energy. 

Summarize the following legislative text with an emphasis on anything relevant to nuclear energy. 
If the external references below clarify or affect interpretation, include them.

Legislative Text:
\"\"\"
{chunk_text}
\"\"\"

External Legal References:
\"\"\"
{external_context}
\"\"\"

Be concise and focus on aspects that might affect nuclear development, funding, tax credits, safety, regulation, or deployment.
Without exception, you should include any changes to things like the inflation reduction act if it's relevant. anything on nuclear fuel supply chain is also
very important to include. Please do not miss these things. This should be 7 PAGES LONG.
"""

    response = client.chat.completions.create(
        model="gpt-4-turbo",  # or "gpt-3.5-turbo" if needed
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

from docx import Document
from docx.shared import Pt

def export_summaries_to_docx(summaries, output_filename="Nuclear_Policy_Summary.docx"):
    doc = Document()

    # Title
    doc.add_heading("Nuclear-Relevant Summary of Legislation", 0)

    # Subtitle
    doc.add_paragraph("This summary aggregates nuclear-related information from the legislative text and referenced legal materials.").italic = True
    doc.add_paragraph(" ")

    # Main content
    for i, summary in enumerate(summaries):
        doc.add_heading(f"Section {i+1}", level=1)
        para = doc.add_paragraph(summary)
        para.style.font.size = Pt(11)

    # Save file
    doc.save(output_filename)
    print(f"📄 Report saved as: {output_filename}")

def summarize_all_summaries(summaries, client):
    joined_summary = "\n\n".join(summaries)

    prompt = (
        "You are a policy analyst. Summarize the following nuclear-related legislative summaries into a cohesive, "
        "concise 7-page report. Make sure to explictly mention things related to nuclear fuel supply chain, and make mention of anything changed from the Inflation Reduction Act, Focus on relevance to nuclear energy, including provisions, repeals, amendments, or "
        "regulatory changes. Remove redundancy, group similar themes, and be succinct:\n\n"
        f"{joined_summary}"
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()

final_summary = summarize_all_summaries(summaries, client)
export_summaries_to_docx([final_summary])