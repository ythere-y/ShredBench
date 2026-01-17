#!/bin/bash

# --- 配置区域 ---
# 如果你的 Python 脚本名不同，请在此处修改
PREPROCESS_SCRIPT="preprocess.py"
BLENDER_SCRIPT="blenderprocess.py"

# --- 脚本逻辑 ---

# 1. 检查文件是否存在
if [[ ! -f "$PREPROCESS_SCRIPT" ]]; then
    echo "错误: 找不到脚本 $PREPROCESS_SCRIPT"
    exit 1
fi

if [[ ! -f "$BLENDER_SCRIPT" ]]; then
    echo "错误: 找不到脚本 $BLENDER_SCRIPT"
    exit 1
fi

# 2. 执行预处理 (Preprocess)
echo "--------------------------------------"
echo "[1/2] 正在开始预处理阶段..."
echo "--------------------------------------"

python "$PREPROCESS_SCRIPT"

# 检查上一步是否成功 (exit code 0 代表成功)
if [ $? -eq 0 ]; then
    echo "✅ 预处理完成。"
else
    echo "❌ 预处理失败，停止执行后续步骤。"
    exit 1
fi

# 3. 执行 Blender 处理
echo ""
echo "--------------------------------------"
echo "[2/2] 正在开始 Blender 处理阶段..."
echo "--------------------------------------"

# 注意：如果是直接运行 python 脚本：
python "$BLENDER_SCRIPT"

# 或者，如果你是想调用 Blender 软件来运行这个 python 脚本，请取消下面这行的注释：
# blender --background --python "$BLENDER_SCRIPT"

if [ $? -eq 0 ]; then
    echo "✅ Blender 处理成功完成！"
else
    echo "❌ Blender 处理过程中出现错误。"
    exit 1
fi
