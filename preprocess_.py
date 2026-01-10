import os
import time
import tempfile
import re
import numpy as np
import markdown
import uuid  
from PIL import Image
from scipy.spatial import cKDTree

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

MDS_DIR = "./my_dataset/code/python"               
ROOT_OUTPUT_DIR = "news_textures_output"
FIXED_PIECE_COUNT = 16       
RENDER_WIDTH = 1600      
FONT_SIZE_PX = 28        
MIN_HEIGHT = 1000        
CHROME_BINARY_PATH = os.path.abspath("./chrome_bin/chrome-linux64/chrome")
DRIVER_PATH = os.path.abspath("./chrome_bin/chromedriver-linux64/chromedriver")

def get_standard_html(html_content):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        body {{
            width: {RENDER_WIDTH}px;
            margin: 0;
            padding: 60px;
            box-sizing: border-box;
            background-color: #fdfbf7;
            font-family: 'Times New Roman', 'SimSun', serif;
            color: #111;
            font-size: {FONT_SIZE_PX}px;
            line-height: 1.6;
        }}
        h1 {{ font-size: 2.2em; border-bottom: 3px solid #333; padding-bottom: 20px; margin-bottom: 40px; text-align: center; }}
        h2 {{ font-size: 1.8em; border-bottom: 1px solid #aaa; margin-top: 50px; padding-bottom: 10px; }}
        h3 {{ font-size: 1.4em; font-weight: bold; margin-top: 30px; }}
        p {{ margin-bottom: 20px; text-align: justify; }}
        ul, ol {{ padding-left: 40px; margin-bottom: 20px; }}
        li {{ margin-bottom: 10px; }}
        pre {{ background: #eee; padding: 20px; border-radius: 5px; overflow-x: auto; font-family: monospace; }}
        code {{ background: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
        img {{ max-width: 90%; display: block; margin: 30px auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 30px 0; }}
        th, td {{ border: 1px solid #999; padding: 12px; text-align: left; }}
        th {{ background-color: #eee; font-weight: bold; }}
        mjx-container {{ font-size: 110% !important; outline: none !important; }}
    </style>
    <script>
    MathJax = {{
      tex: {{ 
          inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
          displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
          processEscapes: true,
          tags: 'ams' 
      }},
      svg: {{ fontCache: 'global' }},
      startup: {{
        pageReady: () => {{
           return MathJax.startup.defaultPageReady().then(() => {{
             document.body.setAttribute('data-render-status', 'done');
             const height = Math.max(document.body.scrollHeight, document.body.offsetHeight, {MIN_HEIGHT});
             document.body.setAttribute('data-height', height);
           }});
        }}
      }}
    }};
    </script>
    <script type="text/javascript" id="MathJax-script" async
      src="https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/tex-svg.js">
    </script>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

def init_driver():
    if not os.path.exists(CHROME_BINARY_PATH):
        raise FileNotFoundError(f"❌ 找不到 Chrome: {CHROME_BINARY_PATH}")
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BINARY_PATH
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={RENDER_WIDTH},4000") 
    service = Service(executable_path=DRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)

def render_markdown_to_long_image(driver, md_text, output_path):
    if "\\n" in md_text or (md_text.strip().startswith('"') and md_text.strip().endswith('"')):
        cleaned_text = md_text.strip()
        if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
            cleaned_text = cleaned_text[1:-1]
        cleaned_text = cleaned_text.replace(r'\n', '\n')
        cleaned_text = cleaned_text.replace(r'\t', '\t')
        cleaned_text = cleaned_text.replace(r'\"', '"')
        
        md_text = cleaned_text
    placeholders = {}
    
    def protect_math(match):
        unique_id = uuid.uuid4().hex
        key = f"MATHMASK{unique_id}END"
        content = match.group(0)
        
        if content.startswith('$$'):
            is_align_block = r'\begin{align}' in content or r'\begin{align*}' in content
            is_aligned = r'\begin{aligned}' in content 
            if is_align_block and not is_aligned:
                content = content[2:-2].strip() 
            
        placeholders[key] = content
        return key

    pattern = re.compile(r'(?:\$\$.*?\$\$)|(?:\$.*?\$)', re.DOTALL)
    md_text_safe = pattern.sub(protect_math, md_text)
    html_body = markdown.markdown(md_text_safe, extensions=['extra', 'nl2br', 'codehilite'])
    for key, val in placeholders.items():
        html_body = html_body.replace(key, val)
    abs_mds_path = os.path.abspath("mds").replace("\\", "/")
    if not abs_mds_path.endswith("/"):
        abs_mds_path += "/"
        
    full_html = get_standard_html(html_body).replace(
        "<head>", 
        f'<head><base href="file://{abs_mds_path}">'
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(full_html)
        temp_path = f.name

    try:
        driver.get(f"file:///{temp_path}")
        try:
            start_t = time.time()
            while time.time() - start_t < 5.0:
                status = driver.execute_script("return document.body.getAttribute('data-render-status');")
                if status == 'done':
                    break
                time.sleep(0.2)
        except:
            pass
        required_height = driver.execute_script("return document.body.getAttribute('data-height') || document.body.scrollHeight")
        required_height = int(float(required_height)) + 100 
        
        driver.set_window_size(RENDER_WIDTH, required_height)
        driver.save_screenshot(output_path)
        
    finally:
        try: os.remove(temp_path)
        except: pass

    apply_paper_texture(output_path)

def apply_paper_texture(image_path):
    try:
        img = Image.open(image_path).convert("RGBA")
        noise = np.random.randint(240, 255, (img.height, img.width, 3), dtype=np.uint8)
        bg = Image.fromarray(noise, mode="RGB").convert("RGBA")
        final = Image.alpha_composite(bg, img)
        final.convert("RGB").save(image_path)
    except Exception as e:
        print(f"Texture error: {e}")

def generate_cut_masks(base_img_path, output_dir, num_pieces):
    try:
        img = Image.open(base_img_path)
    except FileNotFoundError:
        print(f"Skipping {base_img_path}, not found.")
        return

    w, h = img.size
    points = np.random.rand(num_pieces, 2) * [w, h]
    
    scale = 0.5 
    small_w, small_h = int(w * scale), int(h * scale)
    y_grid, x_grid = np.indices((small_h, small_w))
    coords = np.stack((x_grid, y_grid), axis=-1).reshape(-1, 2)
    
    tree = cKDTree(points * scale)
    _, regions = tree.query(coords)
    regions = regions.reshape(small_h, small_w)
    
    os.makedirs(output_dir, exist_ok=True)
    
    for i in range(num_pieces):
        small_mask = (regions == i).astype(np.uint8) * 255
        mask_img = Image.fromarray(small_mask).resize((w, h), resample=Image.NEAREST)
        mask_arr = np.array(mask_img)
        
        rows, cols = np.where(mask_arr > 0)
        if len(rows) == 0: continue
        
        y_min, y_max = rows.min(), rows.max()
        x_min, x_max = cols.min(), cols.max()
        
        pad = 2
        y_min, y_max = max(0, y_min - pad), min(h, y_max + pad)
        x_min, x_max = max(0, x_min - pad), min(w, x_max + pad)

        mask_crop = mask_arr[y_min:y_max, x_min:x_max]
        tex_crop = img.crop((x_min, y_min, x_max, y_max))

        Image.fromarray(mask_crop).save(os.path.join(output_dir, f"mask_{i}.png"))
        tex_crop.save(os.path.join(output_dir, f"tex_{i}.png"))

def main():
    if not os.path.exists(MDS_DIR): 
        print(f"Directory {MDS_DIR} not found.")
        return

    md_files = [f for f in os.listdir(MDS_DIR) if f.lower().endswith('.md')]
    md_files.sort()
    
    driver = init_driver()
    
    print(f"🚀 Blender 数据生成模式 | 处理 {len(md_files)} 个文件...")

    for i, filename in enumerate(md_files):
        try:
            file_path = os.path.join(MDS_DIR, filename)
            item_name = os.path.splitext(filename)[0]
            group_folder = f"group_{FIXED_PIECE_COUNT}_pieces"
            doc_output_dir = os.path.join(ROOT_OUTPUT_DIR, group_folder, item_name)
            if os.path.exists(doc_output_dir):
                print(f"⏭️ [{i+1}/{len(md_files)}] 跳过: {filename} (目录已存在)")
                continue
            os.makedirs(doc_output_dir, exist_ok=True)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            full_img_path = os.path.join(doc_output_dir, "texture_base.png")
            print(f"[{i+1}/{len(md_files)}] 渲染: {filename}")
            
            render_markdown_to_long_image(driver, content, full_img_path)
            
            print(f"    -> 生成 {FIXED_PIECE_COUNT} 个碎片纹理...")
            generate_cut_masks(full_img_path, doc_output_dir, FIXED_PIECE_COUNT)
            
        except Exception as e:
            print(f"❌ Error: {e}")

    driver.quit()
    print("\n✅ 完成！")

if __name__ == "__main__":
    main()