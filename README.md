# ComfyUI-Qwen3.5-Low-VRAM-GPU

本插件使用纯AI生成，已成功运行。
以下内容也使用AI生成，存在一定胡诌成分，谨慎参考。
This plugin is entirely AI-generated and has been successfully run. 
The following content is also AI-generated and may contain some fabrication, so please refer to it with caution.


🤖 在 ComfyUI 中本地运行 Qwen3.0/3.5 GGUF 量化模型，支持图片/视频提示词反推、深度思考模式、低显存优化

---

## ✨ 功能特性

- ✅ **双模型兼容**：支持 Qwen3.0 和 Qwen3.5 系列 GGUF 模型
- ✅ **多模态支持**：图片提示词反推、视频提示词反推
- ✅ **三种运行模式**：
  - 🧠 深度思考模式（复杂推理、数学、代码）
  - ⚡ 指令快速模式（简单对话、快速问答）
  - 🎨 提示词专用模式（图片/视频提示词反推）
- ✅ **显存优化**：
  - 投影模型 (mmproj) 可加载到 CPU 内存，节约 2-3GB 显存
  - 12GB 显存可流畅运行 27B 模型
  - 支持 Flash Attention 2 加速
- ✅ **自定义提示词工程**：支持自定义 system prompt
- ✅ **本地离线运行**：无需网络，无需 API，完全隐私
- ✅ **最新格式支持**：Z-Image Turbo、Flux.2 Klein、Qwen Image 等

---

## 📋 系统要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| **操作系统**  | Windows 11 |
| **显存 (VRAM)** | 12GB+ |
| **内存 (RAM)** | 32GB+ |
| **Python** | 3.11+ |
| **CUDA**   | 13.0|
| **磁盘空间** |50GB+ |

### 显存与模型推荐

| 显存 | 推荐模型 | 量化 | 
|------|---------|---------|
| 12GB | Qwen3.5-27B | Q2_K | 

---

## 🚀 快速安装

### 步骤 1：安装插件

```bash
# 方法 A：手动安装（推荐）
cd .\ComfyUI\custom_nodes
git clone https://github.com/GZT2023/ComfyUI-Qwen3.5-Low-VRAM-GPU.git
```

### 步骤 2：安装依赖

```bash
# 进入插件目录
cd .\ComfyUI\custom_nodes\ComfyUI-Qwen3.5-Low-VRAM-GPU

# 使用 ComfyUI 嵌入式 Python 安装
.\ComfyUI\python_embeded\python.exe -m pip install -r requirements.txt
```

如果出现推理错误，建议从源码编译llama_cpp_python

1. 先卸载官方版本
pip uninstall llama-cpp-python -y

2. 安装 fork 版本（从 GitHub 直接安装）

找一个空的英文路径目录，

git clone https://github.com/JamePeng/llama-cpp-python.git

cd llama-cpp-python

git pull

git submodule update --init --recursive

$env:CMAKE_ARGS = "-DGGML_CUDA=on"

pip install -e .

编译成功后，测试是否成功：
python -c "import llama_cpp; print('CUDA:', llama_cpp.llama_supports_gpu_offload())"
应输出 True



### 步骤 3：下载模型

#### 官方模型页面
🔗 [Qwen3.5-27B 官方页面 (ModelScope)](https://modelscope.cn/models/Qwen/Qwen3.5-27B)

#### GGUF 量化模型下载
🔗 [unsloth/Qwen3.5-27B-GGUF (ModelScope)](https://modelscope.cn/models/unsloth/Qwen3.5-27B-GGUF/)

| 量化版本 | 文件大小 | 显存占用 | 推荐场景 |
|---------|---------|---------|---------|
| Q2_K | ~9.8 GB | 12GB | 测试/低显存 |


#### 多模态投影文件（图片/视频分析必需）

| 文件 | 精度 | 大小 | 推荐 |
|------|------|------|------|
| mmproj-F16.gguf | FP16 | ~1GB | ⭐ 通用推荐 |
| mmproj-BF16.gguf | BF16 | ~1GB | NVIDIA Ampere+ |

或者使用这个多模态投影： 🔗 [lmstudio-community/Qwen3.5-27B-GGUF]（https://modelscope.cn/models/lmstudio-community/Qwen3.5-27B-GGUF）
mmproj-Qwen3.5-27B-BF16.gguf


#### 模型存放路径

```
ComfyUI\models\Qwen-Low-VRAM\

    ├── Qwen3.5-27B-Q2_K.gguf       # 主模型
    └── mmproj-Qwen3.5-27B-BF16.gguf      # 多模态投影
```

### 步骤 4：重启 ComfyUI

```bash
# 关闭 ComfyUI 后重新启动
# 控制台应显示：[Qwen-Low-VRAM] ✓ 插件加载成功
```

---

## 📖 使用指南

### 1. 🤖 Qwen 模型加载器

**节点名称：** `QwenModelLoader`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model_path` | 下拉选择 | - | GGUF 模型文件 |
| `model_version` | 下拉选择 | 自动检测 | Qwen3.0 / Qwen3.5 |
| `mode` | 下拉选择 | 提示词专用模式 | 运行模式选择 |
| `n_gpu_layers` | 整数 | 99 | GPU 卸载层数（-1=全部） |
| `n_ctx` | 整数 | 16384 | 上下文长度 |
| `n_batch` | 整数 | 1024 | 批处理大小 |
| `flash_attn` | 布尔 | True | 启用 Flash Attention |
| `low_vram_mode` | 布尔 | False | 低显存模式 |
| `offload_clip_to_cpu` | 布尔 | True | 投影模型加载到 CPU |
| `mmproj_path` | 下拉选择 | None | 多模态投影文件 |

### 2. 💬 Qwen 文本生成

**节点名称：** `QwenChatCompletion`

**输入：** `qwen_model`、`prompt`、`max_tokens`、`temperature`、`top_p`、`top_k`、`presence_penalty`、`seed`

**输出：** `response`（最终回答）、`thinking_process`（思考过程）、`full_output`（完整输出）

### 3. 🖼️ Qwen 图片提示词反推

**节点名称：** `QwenImagePromptReverse`

**输入：** `qwen_model`、`image`、`output_format`、`detail_level`、`enable_thinking`、`custom_system_prompt`

**输出格式选项：** Z-Image Turbo ⭐、Z-Image Base、Qwen Image、Flux.2 Klein、Stable Diffusion XL、Midjourney V6、DALL-E 3、Flux.1、自定义

**输出：** `prompt`（核心提示词）、`analysis`（画面分析）、`full_output`（完整输出）

### 4. 🎬 Qwen 视频提示词反推

**节点名称：** `QwenVideoPromptReverse`

**输入：** `qwen_model`、`images`、`frame_sample_rate`、`max_frames`、`output_format`、`enable_thinking`、`custom_system_prompt`

**输出格式选项：** Z-Image Turbo、Z-Image Base、Qwen Image、Flux.2 Klein、Stable Video Diffusion、Runway Gen-3、Pika 1.5、自定义

**输出：** `prompt`（核心提示词）、`motion_description`（运动描述）、`full_output`（完整输出）

---

## ⚙️ 性能优化配置（12GB 显存推荐）

| 设置 | 推荐值 | 说明 |
|------|--------|------|
| 量化版本 | Q2_K | 平衡精度和显存 |
| n_gpu_layers | 99 | 全部加载到 GPU |
| n_ctx | 16384 | 减少显存占用 |
| n_batch | 1024 | 提高吞吐量 |
| low_vram_mode | ❌ 关闭 | 12GB 不需要 |
| offload_clip_to_cpu | ✅ 启用 | 节约 2-3GB 显存 |
| flash_attn | ✅ 启用 | 加速 20-30% |

---

## 🔧 常见问题


**Q1: 插件加载失败，报错 `ModuleNotFoundError`**  
A: 确保目录结构正确，运行 `pip install -r requirements.txt`，重启 ComfyUI。

**Q2: 模型加载失败，报错 `Failed to load model`**  
A: 检查模型文件路径是否正确，确认扩展名是 `.gguf`，尝试降低 `n_gpu_layers` 值。

**Q3: 图片分析报错 "未加载多模态投影文件"**  
A: 下载 `mmproj-F16.gguf` 放入 `C:\ComfyUI\models\Qwen-Low-VRAM\`，在模型加载器节点中选择。

**Q4: 显存不足 (OOM)**  
A: 启用 `offload_clip_to_cpu`，减小 `n_gpu_layers`/`n_ctx`/`n_batch`，或使用更低量化版本。

**Q5: 生成速度慢**  
A: 启用 `flash_attn`，增大 `n_gpu_layers`/`n_batch`（显存允许），关闭 `low_vram_mode`。

---

## 📁 插件目录结构

```
ComfyUI-Qwen3.5-Low-VRAM-GPU/
├── __init__.py                 # 插件入口
├── requirements.txt            # 依赖
├── README.md                   # 说明文档
├── nodes/
│   ├── __init__.py             # 节点导入
│   ├── model_loader.py         # 模型加载器
│   ├── chat_completion.py      # 文本生成
│   ├── image_prompt_reverse.py # 图片反推
│   └── video_prompt_reverse.py # 视频反推
└── web/                        # 前端 UI（可选）
```

---

## 📝 更新日志

### v1.1.0 (2026-02-26)
- ✅ 新增自定义 system prompt 输入
- ✅ 更新提示词格式：Z-Image Turbo、Flux.2 Klein、Qwen Image
- ✅ 优化投影模型 CPU 卸载，节约 2-3GB 显存
- ✅ 修复 `chat_template_kwargs` 兼容性问题
- ✅ 修复图像维度处理 bug
- ✅ 统一节点分类为 `Qwen-Low-VRAM`

### v1.0.0 (2026-02-25)
- ✅ 初始版本发布
- ✅ 支持 Qwen3.0/3.5 GGUF 模型
- ✅ 支持思考模式/指令模式/提示词模式切换
- ✅ 支持图片/视频提示词反推
- ✅ 低显存优化 + Flash Attention 2 支持

---

## 🙏 致谢

- ** Qwen **：提供 Qwen3.0/3.5 模型
- **llama.cpp**：提供 GGUF 推理引擎
- **llama-cpp-python**：提供 Python 绑定
- **ComfyUI**：提供节点框架
- **unsloth**：提供动态量化 GGUF 模型
- **lmstudio-community**：提供多模态投影

---

## 📄 许可证

Apache License 2.0

---

> 💡 **提示**：如有问题，请提供操作系统、显存大小、ComfyUI 版本、Python 版本和完整错误日志，让其他人或AI帮你解决。

(本人不懂代码、不懂编程、不懂算法，AI不能解决的，基本都不一定能解决。)

祝你使用愉快！🎉

