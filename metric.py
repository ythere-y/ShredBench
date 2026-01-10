import os
import argparse
import Levenshtein
import statistics
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
import jieba
import re

# NLTK 平滑函数
cc = SmoothingFunction()

def get_args():
    parser = argparse.ArgumentParser(description="Full Evaluation (CER, BLEU, ROUGE)")
    parser.add_argument('--pred_root', type=str, default='inference_results_qwen_plus', help='Root directory of inference results')
    parser.add_argument('--gt_root', type=str, default='my_dataset', help='Root directory of ground truth')
    parser.add_argument('--output_report', type=str, default='evaluation_report_full_qwen_plus.txt', help='Path to save the report')
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

def calculate_metrics(pred, gt):
    # 1. CER (Normalized Levenshtein Distance)
    dist = Levenshtein.distance(pred, gt)
    
    # 【修改点】归一化分母取 pred 和 gt 长度的最大值
    # 这样结果天然在 [0, 1] 之间，不需要再手动置为 1
    max_len = max(len(pred), len(gt))
    
    if max_len > 0:
        cer = dist / max_len
    else:
        # pred 和 gt 都为空字符串
        cer = 0.0

    # 2. BLEU (简单的空格分词)
    pred_tokens = pred.split()
    gt_tokens = gt.split()
    try:
        if len(gt_tokens) == 0:
            bleu = 0.0
        else:
            bleu = sentence_bleu([gt_tokens], pred_tokens, smoothing_function=cc.method1)
    except:
        bleu = 0.0

    # 3. ROUGE-L
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    try:
        if len(gt) == 0:
            rouge_l = 0.0
        else:
            scores = scorer.score(gt, pred)
            rouge_l = scores['rougeL'].fmeasure
    except:
        rouge_l = 0.0

    return cer, bleu, rouge_l


def main():
    args = get_args()
    records = []
    datasets = ['data_8', 'data_12', 'data_16']
    
    print(f"Start Full Evaluation...")

    for dataset_name in datasets:
        pred_dataset_dir = os.path.join(args.pred_root, dataset_name)
        if not os.path.exists(pred_dataset_dir):
            continue
            
        for root, dirs, files in os.walk(pred_dataset_dir):
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                pred_path = os.path.join(root, file)
                rel_path = os.path.relpath(pred_path, start=pred_dataset_dir)
                gt_path = os.path.join(args.gt_root, rel_path)
                
                pred_content = read_file(pred_path)
                gt_content = read_file(gt_path)
                
                if gt_content is None or pred_content is None:
                    continue
                
                cer, bleu, rouge = calculate_metrics(pred_content, gt_content)
                cat, sub = parse_category(rel_path)
                records.append({
                    'dataset': dataset_name, 'cat': cat, 'sub': sub,
                    'cer': cer, 'bleu': bleu, 'rouge': rouge
                })

    if not records:
        print("No files evaluated.")
        return

    def get_stats(filter_func):
        subset = [r for r in records if filter_func(r)]
        if not subset:
            return 0.0, 0.0, 0.0, 0
        avg_cer = statistics.mean([r['cer'] for r in subset])
        avg_bleu = statistics.mean([r['bleu'] for r in subset])
        avg_rouge = statistics.mean([r['rouge'] for r in subset])
        return avg_cer, avg_bleu, avg_rouge, len(subset)

    lines = []
    lines.append("="*100)
    lines.append("                         Full Metrics Evaluation Report                         ")
    lines.append("="*100)
    lines.append(f"Total files: {len(records)}\n")

    header_fmt = "{:<12} | {:^10} | {:^10} | {:^10} | {:^6}"
    row_fmt    = "{:<12} | {:^10.4f} | {:^10.4f} | {:^10.4f} | {:^6}"

    # 1. By Dataset
    lines.append("--- 1. By Dataset ---")
    lines.append(header_fmt.format("Dataset", "CER(↓)", "BLEU(↑)", "ROUGE(↑)", "Count"))
    lines.append("-" * 65)
    for d in datasets:
        c, b, r, n = get_stats(lambda x: x['dataset'] == d)
        lines.append(row_fmt.format(d, c, b, r, n))
    lines.append("")

    # 2. By Category
    unique_cats = sorted(list(set(r['cat'] for r in records)))
    lines.append("--- 2. By Category ---")
    lines.append(header_fmt.format("Category", "CER(↓)", "BLEU(↑)", "ROUGE(↑)", "Count"))
    lines.append("-" * 65)
    for cat in unique_cats:
        c, b, r, n = get_stats(lambda x: x['cat'] == cat)
        lines.append(row_fmt.format(cat, c, b, r, n))
    lines.append("")

    # 3. By Subcategory
    unique_subs = sorted(list(set(r['sub'] for r in records)))
    lines.append("--- 3. By Subcategory ---")
    lines.append(header_fmt.format("Subcategory", "CER(↓)", "BLEU(↑)", "ROUGE(↑)", "Count"))
    lines.append("-" * 65)
    for sub in unique_subs:
        c, b, r, n = get_stats(lambda x: x['sub'] == sub)
        lines.append(row_fmt.format(sub, c, b, r, n))
    lines.append("")

    # 4. Interleaved (With BLEU)
    lines.append("--- 4. Detailed Interleaved ---")
    lines.append("Format: CER / BLEU / ROUGE")
    
    # 增加列宽以容纳三个数据
    col_width = 24
    header = f"{'Subcategory':<12} | " + " | ".join([f"{d:^{col_width}}" for d in datasets])
    lines.append(header)
    lines.append("-" * len(header))

    for sub in unique_subs:
        row = f"{sub:<12} | "
        for d in datasets:
            c, b, r, n = get_stats(lambda x: x['dataset'] == d and x['sub'] == sub)
            if n > 0:
                # 显示 CER / BLEU / ROUGE
                val_str = f"{c:.2f} / {b:.2f} / {r:.2f}"
                row += f"{val_str:^{col_width}} | "
            else:
                row += f"{'N/A':^{col_width}} | "
        lines.append(row)

    with open(args.output_report, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    print("\n".join(lines))
    print(f"\nReport saved to: {os.path.abspath(args.output_report)}")

if __name__ == "__main__":
    main()