import os
import argparse
import statistics
import markdown
import re
from tqdm import tqdm
from table_recognition_metric import TEDS

def get_args():
    parser = argparse.ArgumentParser(description="Table Evaluation (TEDS) Fixed")
    parser.add_argument('--pred_root', type=str, default='inference_results_mistral_reasoning_14b', help='Root directory of inference results')
    parser.add_argument('--gt_root', type=str, default='my_dataset', help='Root directory of ground truth')
    parser.add_argument('--output_report', type=str, default='evaluation_report_table_teds_mistral_reasoning_14b.txt', help='Path to save the report')
    return parser.parse_args()

def read_file(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        return None

def parse_category(rel_path):
    parts = os.path.normpath(rel_path).split(os.sep)
    category = parts[0] if len(parts) > 0 else "unknown"
    if category == 'table':
        subcategory = 'table'
    elif len(parts) > 1:
        subcategory = parts[1]
    else:
        subcategory = "unknown"
    return category, subcategory

def clean_html_attributes(html_str):
    if not html_str: return html_str
    html_str = re.sub(r'colspan=["\']["\']', 'colspan="1"', html_str)
    html_str = re.sub(r'rowspan=["\']["\']', 'rowspan="1"', html_str)
    
    return html_str

def md_to_html(md_content):
    if not md_content:
        return ""
    try:
        html_fragment = markdown.markdown(md_content, extensions=['tables'])
        full_html = f"<html><body>{html_fragment}</body></html>"
        clean_html = clean_html_attributes(full_html)
        
        return clean_html
    except Exception as e:
        # print(f"Markdown Convert Error: {e}")
        return ""

def main():
    args = get_args()
    records = []
    datasets = ['data_8', 'data_12', 'data_16']
    
    print("Initializing TEDS metric...")
    try:
        teds_metric = TEDS(structure_only=False)
    except Exception as e:
        print(f"【严重错误】TEDS 初始化失败: {e}")
        return

    print(f"Start Table Evaluation...")

    for dataset_name in datasets:
        pred_dataset_dir = os.path.join(args.pred_root, dataset_name)
        if not os.path.exists(pred_dataset_dir):
            continue
            
        for root, dirs, files in os.walk(pred_dataset_dir):
            for file in tqdm(files, desc=f"Processing {dataset_name}"):
                if not file.endswith('.md'):
                    continue
                
                pred_path = os.path.join(root, file)
                rel_path = os.path.relpath(pred_path, start=pred_dataset_dir)
                
                category, subcategory = parse_category(rel_path)
                if category != 'table': 
                    continue

                gt_path = os.path.join(args.gt_root, rel_path)
                
                pred_md = read_file(pred_path)
                gt_md = read_file(gt_path)
                
                if gt_md is None or pred_md is None:
                    continue
                
                pred_html = md_to_html(pred_md)
                gt_html = md_to_html(gt_md)

                try:
                    score = teds_metric(pred_html, gt_html)
                except Exception as e:
                    print(f"\n[Skip] Error calculating {file}: {e}")
                    # print(f"Bad HTML: {pred_html}") # 调试用
                    score = 0.0

                records.append({
                    'dataset': dataset_name, 
                    'cat': category, 
                    'sub': subcategory,
                    'teds': score
                })

    if not records:
        print("No table files evaluated.")
        return

    def get_stats(filter_func):
        subset = [r for r in records if filter_func(r)]
        if not subset: return 0.0, 0
        avg_teds = statistics.mean([r['teds'] for r in subset])
        return avg_teds, len(subset)

    lines = []
    lines.append("="*80)
    lines.append("           Table TEDS Evaluation Report           ")
    lines.append("="*80)
    lines.append(f"Total Table files: {len(records)}\n")

    header_fmt = "{:<12} | {:^15} | {:^6}"
    row_fmt    = "{:<12} | {:^15.4f} | {:^6}"

    lines.append("--- 1. By Dataset ---")
    lines.append(header_fmt.format("Dataset", "TEDS(↑)", "Count"))
    lines.append("-" * 40)
    for d in datasets:
        score, n = get_stats(lambda x: x['dataset'] == d)
        lines.append(row_fmt.format(d, score, n))
    lines.append("")

    avg_all, count_all = get_stats(lambda x: True)
    lines.append(f"Overall TEDS: {avg_all:.4f} (over {count_all} tables)")

    with open(args.output_report, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    print("\n" + "\n".join(lines))
    print(f"\nReport saved to: {os.path.abspath(args.output_report)}")

if __name__ == "__main__":
    main()
