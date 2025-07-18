import requests
import fitz  # PyMuPDF
import tiktoken
from openai import OpenAI

# 🔑 Initialize OpenAI client
client = OpenAI(api_key="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")

# 📥 Download PDF from public S3 URL
def download_pdf_from_url(url, filename="BBB_HR1.pdf"):
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

# 📄 Extract all text from PDF
def load_pdf_text(filepath):
    doc = fitz.open(filepath)
    return "\n".join(page.get_text() for page in doc)

# 🔪 Break text into chunks that fit within token limits
def chunk_text(text, max_tokens=1500):
    encoding = tiktoken.encoding_for_model("gpt-4")
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)
        token_count = len(encoding.encode(" ".join(current_chunk)))
        if token_count >= max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

# ✏️ Summarize each chunk, focusing on nuclear energy
def summarize_chunk(chunk):
    prompt = f"""
You are a policy analyst. Summarize only the parts of this legislative text related to nuclear energy, including advanced reactors, tax credits, or research programs. Ignore unrelated content.

Chunk:
\"\"\"
{chunk}
\"\"\"

If no relevant nuclear content is found, respond with: "No relevant nuclear content."
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

# 🧠 Combine summaries into a coherent 2-page document
def combine_summaries(summaries):
    relevant_summaries = [s for s in summaries if "No relevant nuclear content" not in s]
    combined = "\n\n".join(relevant_summaries)

    prompt = f"""
Using the following nuclear-related summaries from a legislative bill, write a clear, structured 2-page summary (1000–1200 words). Group content by topic or section, and use bullet points where helpful.

Summaries:
\"\"\"
{combined}
\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

# 🚀 Run the whole analysis
def main():
    s3_url = "https://my-mapbox-data-geojson.s3.us-east-2.amazonaws.com/BBB_HR1.pdf"  # Replace if needed
    print("📥 Downloading PDF...")
    filename = download_pdf_from_url(s3_url)

    print("📄 Extracting and chunking text...")
    text = load_pdf_text(filename)
    chunks = chunk_text(text)

    summaries = []
    for i, chunk in enumerate(chunks):
        print(f"✏️ Summarizing chunk {i+1}/{len(chunks)}...")
        summaries.append(summarize_chunk(chunk))

    print("🧠 Creating final summary...")
    final_summary = combine_summaries(summaries)

    with open("nuclear_summary.txt", "w", encoding="utf-8") as f:
        f.write(final_summary)

    print("✅ Summary saved to nuclear_summary.txt")

if __name__ == "__main__":
    main()