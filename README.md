<h1 align="center">
ShredBench
</h1>


**ShredBench** is the first benchmark specifically designed to evaluate the **semantic reasoning capabilities** of Multimodal Large Language Models (MLLMs) in **document reconstruction** tasks. Unlike traditional OCR or layout analysis, ShredBench requires models to mentally piece together physically fragmented information, integrating visual pattern recognition with profound language priors.

It features the following characteristics:
- **Multi-Granularity Complexity**: The benchmark partitions images into **8, 12, and 16 fragments** using Voronoi tessellation. This hierarchy enables the analysis of how visual entropy correlates with model performance degradation.
- **Diverse Domains & Scenarios**: It comprises **756 documents** spanning **English and Chinese News** (natural language prose), **Source Code** (Python, C++, Java with strict syntax), and **Scientific Tables** (complex 2D structures).
- **Physics-Based Simulation**: To prevent models from relying on trivial edge matching (visual shortcuts), we utilize a **3D rendering pipeline** (Blender) that simulates real-world artifacts including curling, crumpling, shadows, and irregular jagged edges.
- **Comprehensive Evaluation**: We provide baselines for 14 representative MLLMs, including GPT-5, Gemini 3 Pro, and InternVL series, revealing significant gaps in current multimodal reasoning.

**ShredBench** formulates the problem as a **Set-to-Sequence** task:
- **Input**: A set of unordered, scattered image fragments (potentially rotated and distorted).
- **Output**: The reconstructed, coherent text sequence (or code/HTML).

Currently supported metrics include:
- **NED** (Normalized Edit Distance) - For general text accuracy.
- **TEDS** (Tree-Edit-Distance-based Similarity) - Specifically for table structure evaluation.
- **BLEU & ROUGE-L** - For n-gram overlap and longest common subsequence analysis.

## Table of Contents
- [Updates](#updates)
- [Benchmark Introduction](#benchmark-introduction)
- [Evaluation](#evaluation)
  - [Environment Setup and Running](#environment-setup-and-running)
  - [Inference & Scoring](#inference--scoring)
- [Results](#results)
  - [Overall Performance](#overall-performance)
- [TODO](#todo)
- [Citation](#citation)

## Updates

[2026/02/15] **Initial Release**: Released the ShredBench dataset v1.0, including 756 samples across News, Code, and Table domains with 3 granularities (8, 12, 16 pieces).

[2026/01/20] Paper "ShredBench: Evaluating the Semantic Reasoning Capabilities of Multimodal LLMs in Document Reconstruction" submitted to ACL 2026.

## Benchmark Introduction

ShredBench addresses the gap in evaluating MLLMs on physically disrupted documents. Our pipeline consists of three stages: (1) Data Collection from diverse sources, (2) Shredding Simulation via Voronoi tessellation and Blender 3D physics, and (3) Task Formulation.

<details>
  <summary>【Dataset Construction Pipeline】</summary>

1.  **Rendering**: Raw text/code/tables are rendered into high-resolution images (1600px width) using a headless Chrome browser with random paper textures.
2.  **Voronoi Cutting**: We use a k-d tree algorithm to assign pixels to $N$ seed points ($N \in \{8, 12, 16\}$), creating natural, jagged boundaries.
3.  **3D Synthesis**: Fragments are imported into Blender to apply **Solidify** modifiers (thickness), **Marble/Musgrave textures** (crumpling), and global illumination (shadows).

</details>

<details>
  <summary>【Dataset Format】</summary>

The dataset is organized by domain and granularity. The annotation format is markdown:

```markdown
[
  # News Article 13
**Date:** 2025-12-21

The Jack Ma Foundation has pledged to spend at least 300 million yuan ($45 million) in the next decade to staff rural schools with qualified teachers.

The foundation unveiled on Monday its Jack Ma Rural Pre-Service Teacher Initiative, which aims to draw graduates from normal universities to countryside schools on a five-year program.

This is the foundation’s third initiative supporting rural education development.

For the first phase, starting Jan 21, the foundation said it will cooperate with universities in Hunan, Sichuan and Jilin provinces as well as Chongqing, and channel 100 graduates to villages in the four regions.

Each successful applicant will receive 100,000 yuan in addition to their salary, it said.

To encourage program fellows to stay in rural schools, the foundation has pledged to provide online and offline refresher courses, and allocate mentors to advise on teaching and career development.
]
```
</details>

<details>
  <summary>【Evaluation Categories】</summary>

We evaluate performance across these distinct domains:

```
'Natural Language':
    English News (Standard prose, word redundancy)
    Chinese News (High information density, logograms)

'Source Code' (Syntactic logic & Indentation):
    Python (Whitespace sensitive, difficult for reconstruction)
    C++ (Explicit delimiters like {};)
    Java (Explicit delimiters)

'Structured Data':
    Scientific Tables (Complex 2D spatial dependencies, evaluated via TEDS)
```
</details>

## Evaluation

### Environment Setup and Running

To reproduce the data generation or run the evaluation pipeline, you need to set up the environment and download the necessary rendering tools (Blender and Chrome).

Please execute the following commands in your project root:

```bash
# 1. Download and setup Blender for 3D shredding simulation
wget [https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz](https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz)
mkdir blender
tar -xvf blender-4.0.2-linux-x64.tar.xz -C blender --strip-components=1
rm blender-4.0.2-linux-x64.tar.xz

# 2. Download and setup Headless Chrome for document rendering
wget [https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chrome-linux64.zip](https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chrome-linux64.zip)
unzip chrome-linux64.zip
mv chrome-linux64 chrome_bin
rm chrome-linux64.zip

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run the main processing pipeline
bash run.sh
```

### Inference & Scoring

We provide scripts to evaluate various MLLMs. For example, to evaluate **Qwen-VL-Flash**, run the following command.

**Note**: You need to configure your API keys (e.g., `DASHSCOPE_API_KEY`) in the environment variables or config file before running.

```bash
python surpress.py

python qwen_lv_flash.py

python metric.py
```

The script will:
1. Load the shredded document images.
2. Query the model to reconstruct the content.
3. Calculate metrics (NED, BLEU, ROUGE) against the ground truth.
4. Save the results in the `outputs/` directory.

## Results

### Overall Performance

The following table summarizes the performance of representative models on the ShredBench dataset (Average across all domains). **Gemini 3 Pro** establishes the current State-of-the-Art.

| Model Type | Model | 8 Fragments (NED↓) | 12 Fragments (NED↓) | 16 Fragments (NED↓) |
| :--- | :--- | :---: | :---: | :---: |
| **Proprietary** | **Gemini 3 Pro** | **0.33** | **0.37** | **0.41** |
| | Gemini 3 Flash | 0.34 | 0.40 | 0.44 |
| | GPT-5.1 | 0.77 | 0.81 | 0.82 |
| | GPT-5 Mini | 0.58 | 0.65 | 0.73 |
| **Open-Source** | InternVL3.5-38B | 0.74 | 0.75 | 0.76 |
| | Mistral3-Reasoning | 0.77 | 0.79 | 0.79 |
| | Qwen-VL-Plus | 0.59 | 0.63 | 0.84 |

*Note: Lower NED (Normalized Edit Distance) indicates better performance.*

<details>
  <summary>【Detailed Analysis】</summary>

- **Granularity Impact**: Performance degrades linearly for most models as fragmentation increases ($N=8 \rightarrow 16$). However, advanced models like Gemini 3 Pro show a "flatter" decay curve, suggesting stronger global reasoning capabilities.
- **Domain Differences**:
    - **Code**: Explicitly structured languages (Java, C++) are easier to reconstruct than whitespace-dependent languages (Python).
    - **Tables**: This remains the hardest challenge. Interestingly, Gemini 3 Flash outperforms Pro on tables, possibly due to better preservation of rigid 2D spatial structures.
</details>


## TODO

- [ ] Release the full 756-document dataset on Hugging Face.
- [ ] Add support for "irregular" tearing mechanics (non-linear cuts).
- [ ] Optimize the Blender rendering pipeline for faster batch processing.
- [ ] Add evaluation scripts for DeepSeek-VL and Claude 3.5.

## Citation

If you find this project useful in your research, please consider citing our paper:

```bibtex
@article{shredbench2026,
  title={ShredBench: Evaluating the Semantic Reasoning Capabilities of Multimodal LLMs in Document Reconstruction},
  author={Anonymous},
  journal={ACL Submission},
  year={2026}
}
```
