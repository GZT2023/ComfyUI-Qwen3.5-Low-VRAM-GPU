import os
import folder_paths

# 配置模型目录
PLUGIN_MODEL_DIR = "Qwen-Low-VRAM"
folder_paths.add_model_folder_path(PLUGIN_MODEL_DIR, os.path.join(folder_paths.models_dir, PLUGIN_MODEL_DIR))

from llama_cpp import Llama

class QwenModelLoader:
    """
    Qwen3.0/3.5 模型加载器
    支持 GGUF 格式模型，兼容多模态
    """
    
    @classmethod
    def INPUT_TYPES(s):
        llm_files = folder_paths.get_filename_list(PLUGIN_MODEL_DIR)
        llm_files = [f for f in llm_files if f.lower().endswith('.gguf') and not f.lower().startswith('mmproj')]
        
        mmproj_files = ["None"] + [f for f in folder_paths.get_filename_list(PLUGIN_MODEL_DIR) 
                                    if f.lower().startswith('mmproj') and f.lower().endswith('.gguf')]
        
        return {
            "required": {
                "model_path": (llm_files, {"default": llm_files[0] if llm_files else ""}),
                "model_version": (["Qwen3.0", "Qwen3.5", "自动检测"], {"default": "自动检测"}),
                "mode": (["🧠 深度思考模式", "⚡ 指令快速模式", "🎨 提示词专用模式"], {
                    "default": "🎨 提示词专用模式"
                }),
                "n_gpu_layers": ("INT", {
                    "default": 99,
                    "min": -1,
                    "max": 100,
                    "step": 1,
                    "display": "number"
                }),
                "n_ctx": ("INT", {
                    "default": 16384,
                    "min": 4096,
                    "max": 131072,
                    "step": 4096
                }),
                "n_batch": ("INT", {
                    "default": 1024,
                    "min": 128,
                    "max": 2048,
                    "step": 128
                }),
                "flash_attn": ("BOOLEAN", {
                    "default": True,
                    "label": "启用 Flash Attention"
                }),
                "low_vram_mode": ("BOOLEAN", {
                    "default": False,
                    "label": "低显存模式 (12GB 以下推荐)"
                }),
                "offload_clip_to_cpu": ("BOOLEAN", {
                    "default": True,
                    "label": "投影模型加载到 CPU 内存 (节约显存)"
                }),
            },
            "optional": {
                "mmproj_path": (mmproj_files, {"default": "None"}),
            }
        }

    RETURN_TYPES = ("QWEN_MODEL",)
    RETURN_NAMES = ("qwen_model",)
    FUNCTION = "load_model"
    CATEGORY = "Qwen-Low-VRAM"

    def load_model(self, model_path, model_version, mode, n_gpu_layers, n_ctx, n_batch, 
                   flash_attn, low_vram_mode, offload_clip_to_cpu, mmproj_path="None"):
        
        print(f"\n[Qwen-Low-VRAM] ==========================================")
        print(f"[Qwen-Low-VRAM] 开始加载模型...")
        
        model_full_path = folder_paths.get_full_path(PLUGIN_MODEL_DIR, model_path)
        
        if not model_full_path or not os.path.exists(model_full_path):
            raise FileNotFoundError(f"❌ 错误：找不到模型文件！路径：{model_full_path}")
            
        file_size_gb = os.path.getsize(model_full_path) / (1024**3)
        print(f"[Qwen-Low-VRAM] ✓ 模型文件存在：{model_path} ({file_size_gb:.2f} GB)")

        mmproj_full_path = None
        if mmproj_path != "None":
            mmproj_full_path = folder_paths.get_full_path(PLUGIN_MODEL_DIR, mmproj_path)
            if not os.path.exists(mmproj_full_path):
                print(f"[Qwen-Low-VRAM] ⚠️ 警告：MMProj 文件不存在：{mmproj_path}")
                mmproj_full_path = None
            else:
                mmproj_size_gb = os.path.getsize(mmproj_full_path) / (1024**3)
                print(f"[Qwen-Low-VRAM] ✓ 多模态投影：{mmproj_path} ({mmproj_size_gb:.2f} GB)")
                if offload_clip_to_cpu:
                    print(f"[Qwen-Low-VRAM] ⚡ 投影模型将加载到 CPU 内存 (节约约{mmproj_size_gb:.1f}GB 显存)")

        if low_vram_mode:
            n_gpu_layers = min(n_gpu_layers, 30) if n_gpu_layers > 0 else 30
            n_batch = min(n_batch, 256)
            print(f"[Qwen-Low-VRAM] ⚡ 低显存模式已启用：GPU 层数={n_gpu_layers}, 批处理={n_batch}")

        llama_kwargs = {
            "model_path": model_full_path,
            "n_ctx": n_ctx,
            "n_batch": n_batch,
            "n_gpu_layers": n_gpu_layers,
            "verbose": False,
            "flash_attn": flash_attn,
            "offload_kqv": True,
        }

        if mmproj_full_path:
            if offload_clip_to_cpu:
                llama_kwargs["clip_model_path"] = mmproj_full_path
                llama_kwargs["n_gpu_layers_clip"] = 0
                print(f"[Qwen-Low-VRAM] ✓ CLIP 投影模型强制加载到 CPU 内存")
            else:
                llama_kwargs["clip_model_path"] = mmproj_full_path
                print(f"[Qwen-Low-VRAM] ✓ CLIP 投影模型加载到 GPU 显存")

        try:
            print(f"[Qwen-Low-VRAM] 正在初始化 Llama 引擎...")
            print(f"[Qwen-Low-VRAM] 模型版本：{model_version}")
            print(f"[Qwen-Low-VRAM] 模式：{mode}")
            print(f"[Qwen-Low-VRAM] GPU 层数：{n_gpu_layers}")
            print(f"[Qwen-Low-VRAM] 上下文：{n_ctx}")
            print(f"[Qwen-Low-VRAM] Flash Attention: {flash_attn}")
            print(f"[Qwen-Low-VRAM] 投影模型 CPU 卸载：{offload_clip_to_cpu}")
            
            llm = Llama(**llama_kwargs)
            
            print(f"[Qwen-Low-VRAM] ✅ 模型加载成功！")
            print(f"[Qwen-Low-VRAM] ==========================================\n")

        except Exception as e:
            print(f"\n[Qwen-Low-VRAM] ❌ 模型加载失败：{str(e)}")
            print(f"\n[Qwen-Low-VRAM] 💡 建议:")
            print(f"   1. 降低 n_gpu_layers (如设为 50)")
            print(f"   2. 减小 n_ctx (如设为 16384)")
            print(f"   3. 启用低显存模式")
            print(f"   4. 确保投影模型加载到 CPU")
            raise e

        enable_thinking = (mode != "⚡ 指令快速模式")
        
        default_temp = 0.7 if mode == "🎨 提示词专用模式" else (1.0 if enable_thinking else 0.7)
        default_top_p = 0.9 if mode == "🎨 提示词专用模式" else (0.95 if enable_thinking else 0.8)

        model_info = {
            "llm": llm,
            "enable_thinking": enable_thinking,
            "default_temp": default_temp,
            "default_top_p": default_top_p,
            "mode": mode,
            "model_version": model_version,
            "mmproj_path": mmproj_full_path,
            "offload_clip_to_cpu": offload_clip_to_cpu
        }

        return (model_info,)