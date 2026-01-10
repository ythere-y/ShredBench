import requests
from bs4 import BeautifulSoup
import time
import random
import sys
import os
import json
import re
import tarfile
import shutil
# from github import Github
# import arxiv
# import pypandoc
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_chinadaily_content(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8' 
        soup = BeautifulSoup(resp.content, "lxml")

        content_div = soup.find("div", {"id": "Content"})
        if not content_div:
            content_div = soup.find("div", class_="lft_art")
        
        if not content_div:
            return None 
            
        paragraphs = content_div.find_all("p")
        text_list = []
        for p in paragraphs:
            txt = p.get_text().strip()
            if len(txt) > 20:
                text_list.append(txt)
                
        return "\n\n".join(text_list)
    except Exception:
        return None

def get_people_content(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.encoding = resp.apparent_encoding 
        soup = BeautifulSoup(resp.text, "lxml")
        content_div = soup.find("div", class_="rm_txt") or \
                      soup.find("div", class_="layout w1000 txt_con") or \
                      soup.find("div", class_="col col-1 fl") or \
                      soup.find("article")
        
        if not content_div:
            return None

        paragraphs = content_div.find_all("p")
        text_list = []
        for p in paragraphs:
            txt = p.get_text().strip()
            if len(txt) > 20 and "责任编辑" not in txt:
                text_list.append(txt)
                
        return "\n\n".join(text_list)
    except:
        return None

def crawl_news_en(target_count, min_len, max_len):
    articles = []
    seen_urls = set()     
    seen_contents = set()  
    
    rss_urls = [
        "http://www.chinadaily.com.cn/rss/china_rss.xml",
        "http://www.chinadaily.com.cn/rss/world_rss.xml",
        "http://www.chinadaily.com.cn/rss/bizchina_rss.xml",
        "http://www.chinadaily.com.cn/rss/opinion_rss.xml"
    ]
    
    print(f"正在抓取 English News (China Daily)...")
    
    for rss_url in rss_urls:
        if len(articles) >= target_count: break
        
        try:
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.content, features="xml")
            items = soup.find_all("item")
            
            for item in items:
                if len(articles) >= target_count: break
                
                link = item.link.text.strip()
                if link in seen_urls: continue
                seen_urls.add(link)
                pub_date = item.pubDate.text.strip() if item.pubDate else time.strftime("%Y-%m-%d")
                content = get_chinadaily_content(link)
                if not content: continue
                if content in seen_contents: 
                    continue
                
                if min_len <= len(content) <= max_len:
                    seen_contents.add(content)
                    articles.append({
                        "type": "text",
                        "language": "en",
                        "content": content,
                        "date": pub_date
                    })
                    print(f"✅ [News-EN] Got: {len(articles)}/{target_count}")
                    time.sleep(0.5)

        except Exception as e:
            print(f"RSS Error: {e}")
            continue
            
    return articles

def crawl_news_zh(target_count, min_len, max_len):
    articles = []
    seen_urls = set()      # URL 查重
    seen_contents = set()  # 内容查重 (新增)
    
    print(f"正在抓取 Chinese News (人民网)...")
    
    timestamp = int(time.time() * 1000)
    api_url = f"http://news.people.com.cn/210801/211150/index.js?_={timestamp}"
    
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        data = resp.json()
        items = data.get("items", [])
        
        for item in items:
            if len(articles) >= target_count: break
            url = item.get("url")
            date_str = item.get("date", time.strftime("%Y-%m-%d"))
            if url.startswith("/"):
                url = "http://paper.people.com.cn" + url
            elif not url.startswith("http"):
                url = "http://news.people.com.cn" + url
            if url in seen_urls: continue
            seen_urls.add(url)
            content = get_people_content(url)
            if not content: continue
            if content in seen_contents:
                continue
            
            if min_len <= len(content) <= max_len:
                seen_contents.add(content) 
                articles.append({
                    "type": "text",
                    "language": "zh",
                    "content": content,
                    "date": date_str
                })
                print(f"✅ [News-ZH] Got: {len(articles)}/{target_count}")
                time.sleep(0.3)
                
    except Exception as e:
        print(f"API Error: {e}")
        
    return articles

def crawl_news(language, target_count, min_len=800, max_len=2500):
    if language == 'zh':
        return crawl_news_zh(target_count, min_len, max_len)
    else:
        return crawl_news_en(target_count, min_len, max_len)

from github import Github
from github import Auth
import time

from github import Github
from github import Auth
import time

def crawl_github_code_with_date(language, target_count, github_token, min_len=1000, max_len=4000):
    collected = []
    auth = Auth.Token(github_token)
    g = Github(auth=auth)
    ext = 'py' if language == 'python' else language
    query = f"language:{language} size:>=1 extension:{ext}"
    
    print(f"🚀 [日期增强版] 搜索 {language} | 目标: {target_count} | 正在获取...")
    try:
        result = g.search_code(query=query, sort="indexed", order="desc")
        
        total_checked = 0
        
        for file in result:
            if len(collected) >= target_count:
                print(f"\n✨ {language} 任务达成！")
                break
            
            if total_checked > 2000: break
            total_checked += 1
            print(f"\r[{len(collected)}/{target_count}] 检查: {file.name} ... ", end="", flush=True)
            try:
                if file.encoding is None: continue
                content = file.decoded_content.decode('utf-8', errors='ignore')
                length = len(content)

                if min_len <= length <= max_len:
                    date_str = "Unknown"
                    try:
                        repo = file.repository
                        commits = repo.get_commits(path=file.path)
                        if commits.totalCount > 0:
                            last_commit = commits[0]
                            commit_date = last_commit.commit.author.date
                            date_str = commit_date.strftime("%Y-%m-%d")
                    except Exception as e:
                        pass 
                    md_content = f"```{language}\n{content}\n```"
                    collected.append({
                        "type": "code",
                        "language": language,
                        "content": md_content,
                        "date": date_str  # ✅ 
                    })
                    
                    print(f" ✅ 收录 (日期: {date_str})")
                    time.sleep(0.5) 
                else:
                    pass

            except Exception as e:
                time.sleep(1)
                continue
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")

    return collected

def is_clean_html_table(html_content):
    latex_patterns = [
        r'\\frac\{', r'\\sqrt\{', r'\\begin\{', r'\\end\{', 
        r'\\mathbb\{', r'\\mathcal\{', r'\\mathbf\{', 
        r'\\multicolumn', r'\\multirow', r'\\resizebox'
    ]
    
    for pattern in latex_patterns:
        if re.search(pattern, html_content):
            return False, "含 Latex 命令"
    if html_content.count('$') >= 4: 
        return False, "含未转换公式($)"
    if html_content.count('\\') > 5:
        return False, "含过多反斜杠"
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text().strip()
    if len(text) < 20: 
        return False, "内容过少"

    return True, "通过"

def crawl_arxiv_tables(target_count, min_len=800, max_len=15000): 
    collected = []
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.CL", 
        "start": 0,
        "max_results": target_count * 5, 
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    temp_dir = "temp_arxiv_tables"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    print(f"--- 🚀 开始抓取高纯度表格 (目标: {target_count}) ---")

    LATEX_WRAPPER = r"""
    \documentclass{article}
    \usepackage{booktabs}
    \usepackage{multirow}
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{graphicx}
    \usepackage{longtable}
    \begin{document}
    %CONTENT%
    \end{document}
    """

    try:
        print("Step 1: 获取论文列表...")
        resp = requests.get(base_url, params=params, timeout=20)
        soup = BeautifulSoup(resp.content, "html.parser")
        
        entries = soup.find_all("entry")
        print(f"Step 1: 获取到 {len(entries)} 篇候选论文")

        for i, entry in enumerate(entries):
            if len(collected) >= target_count: break
            
            paper_id = entry.id.text.strip().split("/abs/")[-1].split("v")[0]
            date_str = entry.published.text.strip().split("T")[0]
            
            print(f"\n[{len(collected)}/{target_count}] 论文 {paper_id}", end="", flush=True)
            download_url = f"https://arxiv.org/e-print/{paper_id}"
            tar_path = os.path.join(temp_dir, f"{paper_id}.tar.gz")
            try:
                r = requests.get(download_url, stream=True, timeout=15)
                if 'pdf' in r.headers.get('Content-Type', '').lower():
                    print(" -> [纯PDF跳过]", end="")
                    continue
                with open(tar_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024): f.write(chunk)
            except:
                print(" -> [下载失败]", end="")
                continue

            # --- 解压 ---
            extract_path = os.path.join(temp_dir, f"ext_{paper_id}")
            if os.path.exists(extract_path): shutil.rmtree(extract_path)
            try:
                with tarfile.open(tar_path) as tar:
                    tar.extractall(path=extract_path)
            except: pass

            # --- 扫描与转换 ---
            tex_files = []
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    if file.endswith(".tex"):
                        tex_files.append(os.path.join(root, file))
            
            if not tex_files:
                print(" -> [无Tex]", end="")
                continue

            good_tables_count = 0
            
            for tex_file in tex_files:
                if len(collected) >= target_count: break
                
                try:
                    with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    raw_tables = re.findall(r'(\\begin\{table\*?\}.*?\\end\{table\*?\})', content, re.DOTALL)
                    
                    for raw_tex in raw_tables:
                        if len(collected) >= target_count: break

                        # 1. 预清洗
                        clean_tex = re.sub(r'\\resizebox\{.*?\}\{!\}\{', '', raw_tex)
                        clean_tex = re.sub(r'\\input\{.*?\}', '', clean_tex)
                        clean_tex = re.sub(r'\\label\{.*?\}', '', clean_tex) 
                        
                        full_doc = LATEX_WRAPPER.replace("%CONTENT%", clean_tex)
                        
                        # 2. 转换
                        try:
                            html_output = pypandoc.convert_text(
                                full_doc, 'html', format='latex', extra_args=['--mathml']
                            )
                            
                            if "<table" in html_output:
                                soup_table = BeautifulSoup(html_output, 'html.parser').find('table')
                                if soup_table:
                                    final_html = str(soup_table)
                                    
                                    # 3. 质量检测
                                    is_clean, reason = is_clean_html_table(final_html)
                                    
                                    if is_clean:
                                        if min_len <= len(final_html) <= max_len:
                                            collected.append({
                                                "type": "table", "source": paper_id,
                                                "content": final_html, "date": date_str
                                            })
                                            good_tables_count += 1
                                            print("✅", end="", flush=True) 
                                    else:
                                        print("x", end="", flush=True) 

                        except: continue
                except: continue 

            if good_tables_count == 0:
                print(" -> [无优质表格]", end="")
            if os.path.exists(extract_path): shutil.rmtree(extract_path)
            if os.path.exists(tar_path): os.remove(tar_path)

    except Exception as e:
        print(f"\n❌ 错误: {e}")

    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    print(f"\n✅ 任务完成！共筛选出 {len(collected)} 个优质表格。")
    return collected

def save_data_to_files(dataset, base_dir="dataset_output"):
    if not dataset:
        print("❌ 没有收集到任何数据，请检查网络或 Token。")
        return

    metadata_lines = ["Filename | Date | Source/Type"]
    print(f"\n正在保存文件到 {base_dir} ...")
    
    counters = {}

    for item in dataset:
        data_type = item.get('type')
        content = item.get('content')
        date_str = item.get('date', 'Unknown')
        
        if not content: continue
        if data_type == 'text':
            lang = item.get('language')
            save_path = os.path.join(base_dir, "news", lang)
            prefix = "news"
        elif data_type == 'code':
            lang = item.get('language')
            folder_lang = "cpp" if lang in ["cpp", "c++"] else lang
            save_path = os.path.join(base_dir, "code", folder_lang)
            prefix = "code"
        elif data_type == 'table':
            save_path = os.path.join(base_dir, "tables", "arxiv")
            prefix = "table"
        else:
            continue

        os.makedirs(save_path, exist_ok=True)
        key = f"{data_type}_{item.get('language', 'arxiv')}"
        counters[key] = counters.get(key, 0) + 1
        index = counters[key]
        filename = f"{prefix}_{index:03d}.md"
        full_path = os.path.join(save_path, filename)

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                if data_type == 'text':
                    f.write(f"# News Article {index}\n")
                    f.write(f"**Date:** {date_str}\n\n")
                    f.write(content)
                elif data_type == 'code':
                    f.write(f"\n")
                    f.write(content)
                elif data_type == 'table':
                    f.write(f"\n")
                    f.write(content)
            
            relative_path = os.path.join(os.path.basename(save_path), filename)
            metadata_lines.append(f"{relative_path} | {date_str} | {data_type}")
        except Exception as e:
            print(f"Write Error: {e}")

    with open(os.path.join(base_dir, "metadata.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(metadata_lines))
    print("所有任务完成！")

# ==========================================
# Main Entry
# ==========================================
def main():
    # 你的 Token
    GITHUB_TOKEN = "xxxxxx" 
    
    all_data = []
    
    # 1. News
    all_data.extend(crawl_news('zh', 50))
    all_data.extend(crawl_news('en', 50))
    
    # 2. Code
    all_data.extend(crawl_github_code_with_date('python', 33, GITHUB_TOKEN))
    all_data.extend(crawl_github_code_with_date('cpp', 33, GITHUB_TOKEN))
    all_data.extend(crawl_github_code_with_date('java', 33, GITHUB_TOKEN))
    
    # 3. Table
    # all_data.extend(crawl_arxiv_tables(150))
    
    # 4. Save
    save_data_to_files(all_data, base_dir="my_dataset")

if __name__ == "__main__":
    main()