import os
import subprocess

# 配置路径
INPUT_DIR = "final_renders"
OUTPUT_DIR = "final_result"

# 确保输出目录存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"已创建输出目录: {OUTPUT_DIR}")

def main():
    # 获取所有 png 文件
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".png")]
    total = len(files)
    
    if total == 0:
        print("❌ 没有在 final_renders 下找到 PNG 文件")
        return

    print(f"找到 {total} 张图片，开始压缩...")

    for i, filename in enumerate(files):
        # 构建输入输出路径
        input_path = os.path.join(INPUT_DIR, filename)
        
        # 将后缀从 .png 换成 .jpg
        name_no_ext = os.path.splitext(filename)[0]
        output_filename = f"{name_no_ext}.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # 构建 ffmpeg 命令
        # -y 参数表示如果目标文件存在则直接覆盖，不询问
        # -loglevel error 减少输出干扰，只显示报错
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-q:v", "3",
            "-loglevel", "error", 
            output_path
        ]
        
        print(f"[{i+1}/{total}] 正在压缩: {filename} -> {output_filename}")
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"❌ 压缩失败: {filename}")
        except FileNotFoundError:
            print("❌ 错误: 未找到 ffmpeg，请确保已安装并添加到系统环境变量。")
            return

    print(f"\n✅ 全部完成！压缩后的图片在 {OUTPUT_DIR} 文件夹中。")

if __name__ == "__main__":
    main()