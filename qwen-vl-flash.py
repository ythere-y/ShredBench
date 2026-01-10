import os
import base64
import time
import argparse
import concurrent.futures
from io import BytesIO
from PIL import Image
from openai import OpenAI

# --- Default Configuration for Qwen ---
DEFAULT_API_KEY = "xxxxxx"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"

# --- Core Prompt (Unchanged) ---
PROMPT = r"""You are an AI assistant specialized in reconstructing and converting torn document fragments to Markdown format. The input image contains scattered fragments of a single original document. Your task is to mentally "stitch" them together and recover the original content exactly as it was.

Please follow these instructions for the reconstruction and conversion:

1. Reconstruction & Text Processing:
   - **Stitching Logic**: Visually analyze the fragments to determine their logical order. If a sentence or word is cut by a tear (e.g., "pro" on one piece, "cess" on another), merge them into the complete word ("process").
   - **Ignore Artifacts**: Ignore physical damage, tear lines, shadows, and background noise. Do not output text describing the damage.
   - **Verbatim Transcription**: Accurately recognize all text. **Do not summarize, interpret, or hallucinate content.** If the document appears to be code, transcribe the code exactly.
   - Convert the reconstructed text into Markdown format.
   - Maintain the original document structure (headings, paragraphs, lists).

2. Mathematical Formula Processing:
   - Convert all mathematical formulas to LaTeX format.
   - **Reconstruction**: If a formula is split across fragments, reconstruct the valid, complete LaTeX formula.
   - Enclose inline formulas with \( \). For example: This is an inline formula \( E = mc^2 \)
   - Enclose block formulas with \\[ \\]. For example: \[ \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \]

3. Table Processing:
   - Convert tables to HTML format.
   - **Reconstruction**: Realign columns or rows that are split across fragments.
   - Wrap the entire table with <table> and </table>.

4. Figure Handling:
   - Ignore figures content in the image. Do not attempt to describe or convert images.

5. Output Format:
   - Ensure the output Markdown document has a clear structure with appropriate line breaks between elements.
   - **Strict Constraint**: Output ONLY the converted Markdown content. Do not add any introductory text (like "Here is the reconstructed text") or concluding remarks.

Please strictly follow these guidelines. Your primary goal is high-fidelity restoration of the text, formulas, and tables into the specified format.
"""

def get_args():
    parser = argparse.ArgumentParser(description="Document Restoration Inference Script (Qwen)")
    parser.add_argument('--input_roots', nargs='+', default=['data_8', 'data_12', 'data_16'], help='List of input root directories')
    parser.add_argument('--output_dir', type=str, default='inference_results_qwen_flash', help='Root path to save markdown results')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL, help='Model name to use')
    parser.add_argument('--workers', type=int, default=20, help='Number of concurrent threads')
    parser.add_argument('--filter', nargs='+', default=None, help='List of keywords to filter (e.g. python java)')
    parser.add_argument('--api_key', type=str, default=DEFAULT_API_KEY, help='API Key')
    parser.add_argument('--base_url', type=str, default=DEFAULT_BASE_URL, help='Base URL')
    return parser.parse_args()

def encode_image_to_base64(image_path, max_size=2048):
    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            if max(width, height) > max_size:
                ratio = max_size / max(width, height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=95)
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[Error] Encoding image {image_path}: {e}")
        return None

def process_image_with_model(client, model_name, base64_image):
    """
    Process image using streaming API with thinking capability enabled.
    Accumulates only the final answer content.
    """
    try:
        response_stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            }
                        }
                    ]
                }
            ],
            stream=True,
            extra_body={
                "enable_thinking": True,
                # "thinking_budget": 4096 # Optional: Control thinking token budget
            }
        )
        
        full_content = []
        for chunk in response_stream:
            if not chunk.choices:
                continue
                
            delta = chunk.choices[0].delta
            if delta.content:
                full_content.append(delta.content)

        return "".join(full_content)

    except Exception as e:
        print(f"[API Error] Request Failed: {e}")
        return None

def worker_task(file_info):
    input_path, output_path, model_name, api_key, base_url = file_info
    if os.path.exists(output_path):
        return f"[Skip] {os.path.basename(input_path)} (Already exists)"

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=180.0 
    )

    base64_img = encode_image_to_base64(input_path)
    if not base64_img:
        return f"[Fail] Encoding {os.path.basename(input_path)}"

    max_retries = 3
    markdown_content = None
    
    for attempt in range(max_retries):
        markdown_content = process_image_with_model(client, model_name, base64_img)
        if markdown_content:
            break
        time.sleep(1 + attempt) 
    
    if markdown_content:
        cleaned_content = markdown_content.replace("```markdown", "").replace("```", "").strip()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        return f"[Done] {os.path.basename(input_path)} -> {os.path.basename(output_path)}"
    else:
        return f"[Fail] Processing {os.path.basename(input_path)} after retries"

def main():
    args = get_args()
    
    print(f"Model: {args.model}")
    print(f"Base URL: {args.base_url}")
    print(f"Input Roots: {args.input_roots}")
    print(f"Filter: {args.filter if args.filter else 'None (Process All)'}") 
    print(f"Output Dir: {args.output_dir}")
    print(f"Concurrency: {args.workers} workers")

    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    tasks = []
    skipped_count = 0

    print("Scanning files and checking existing results...")

    for root_dir in args.input_roots:
        if not os.path.exists(root_dir):
            print(f"Warning: Input directory '{root_dir}' does not exist.")
            continue
            
        for current_root, dirs, files in os.walk(root_dir):
            for name in files:
                if name.lower().endswith(image_extensions):
                    input_path = os.path.join(current_root, name)
                    
                    if args.filter:
                        normalized_path = input_path.replace("\\", "/").lower()
                        if not any(keyword.lower() in normalized_path for keyword in args.filter):
                            continue

                    rel_path = os.path.relpath(input_path, start=".") 
                    if rel_path.startswith(".."):
                         rel_path = os.path.relpath(input_path, start=os.path.dirname(root_dir))
                    
                    base_name = os.path.splitext(rel_path)[0] + ".md"
                    output_path = os.path.join(args.output_dir, base_name)
                    
                    if os.path.exists(output_path):
                        skipped_count += 1
                        continue

                    tasks.append((input_path, output_path, args.model, args.api_key, args.base_url))

    print("-" * 50)
    print(f"Total files found (matching filter): {len(tasks) + skipped_count}")
    print(f"Skipped (already done): {skipped_count}")
    print(f"Remaining tasks to process: {len(tasks)}")
    print("-" * 50)
    
    if len(tasks) == 0:
        print("All tasks are already completed!")
        return

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_file = {executor.submit(worker_task, task): task for task in tasks}
        
        processed_count = 0
        for future in concurrent.futures.as_completed(future_to_file):
            result = future.result()
            processed_count += 1
            print(f"[{processed_count}/{len(tasks)}] {result}")

    end_time = time.time()
    print(f"\nAll remaining tasks completed in {end_time - start_time:.2f} seconds.")
    print(f"Results saved to: {args.output_dir}")

if __name__ == "__main__":
    main()