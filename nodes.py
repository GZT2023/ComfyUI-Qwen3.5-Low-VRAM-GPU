import os
import json
import torch
import re
import gc
from PIL import Image
import folder_paths
import comfy.model_management as model_management
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

from .utils import image_process, tensor_to_pil, download_from_modelscope

# ========== 全局模型缓存管理（增强自动卸载）==========
_current_model = None          # 当前加载的模型包装器
_current_model_key = None      # 用于比较的键 (model_name, quantization)

def unload_current_model():
    """强制卸载当前全局模型，彻底释放内存和显存"""
    global _current_model, _current_model_key
    if _current_model is not None:
        print(f"[ModelManager] 正在强制卸载旧模型...")
        _current_model.unload()
        _current_model = None
        _current_model_key = None

        # 强制垃圾回收
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("[ModelManager] 旧模型已彻底卸载")

# ========== 模型映射加载 ==========
PLUGIN_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(PLUGIN_DIR, "configs", "default_qwen_vl.json")
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    MODEL_CONFIG = json.load(f)
MODEL_NAMES = list(MODEL_CONFIG.keys())

# ========== 默认提示词 ==========
DEFAULT_SYSTEM_PROMPT = "You are a professional image captioning assistant. Describe the image in detail, including subjects, actions, scene, objects, and any visible text. Use clear and concise natural language. Do not include any evaluations, opinions, or markdown formatting. The description should be suitable for training image generation models."
DEFAULT_USER_PROMPT = "请描述这张图片。"


class Qwen35ModelWrapper:
    """模型包装器，负责加载和推理（支持彻底卸载和状态检查）"""
    def __init__(self):
        self.processor = None
        self.model = None
        self.device = None
        self.model_name = None
        self.quant = None
        self._loaded = False  # 标记模型是否已加载

    def load_model(self, model_path, quant=None, use_cpu=False, use_flash_attn=False,
                   cache_dir=None, model_name="", quant_str=""):
        """
        加载模型，model_path 必须是本地文件系统路径。
        """
        self.model_name = model_name
        self.quant = quant_str
        quant_config = None
        compute_dtype = torch.float16
        if quant == "4bit":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=True
            )
        elif quant == "8bit":
            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=True
            )

        device = "cpu" if use_cpu else "auto"
        attn_impl = "sdpa" if use_flash_attn else None

        load_kwargs = {
            "device_map": device,
            "quantization_config": quant_config,
            "trust_remote_code": True,
            "local_files_only": True,          # 强制只使用本地文件，杜绝HuggingFace联网
            "attn_implementation": attn_impl,
            "cache_dir": cache_dir,
        }
        if quant_config is not None:
            load_kwargs["torch_dtype"] = compute_dtype

        print(f"[Qwen35ModelWrapper] 从本地路径加载模型: {model_path}")
        self.model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
        self.model.eval()
        self.processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
            local_files_only=True,
            cache_dir=cache_dir
        )
        self.device = next(self.model.parameters()).device if not use_cpu else torch.device("cpu")
        self._loaded = True

    def generate_caption(self, images, system_prompt, user_prompt,
                         temperature=0.0, top_p=0.0, max_new_tokens=1024,
                         image_size=1024, disable_think=True):
        # 检查模型是否已加载
        if not self._loaded or self.model is None:
            raise RuntimeError("模型未加载或已被卸载。请重新执行 LoadQwen35Model 节点加载模型，并确保工作流顺序正确。")

        # 预处理图像
        processed_images = []
        for img in images:
            img_np = image_process(img, image_size)
            processed_images.append(Image.fromarray(img_np))

        # 构造对话模板
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": user_prompt}
            ]
        })
        text = self.processor.apply_chat_template(messages, tokenize=False,
                                                  add_generation_prompt=True, enable_thinking=False)

        # 批量编码
        inputs = self.processor(
            images=processed_images,
            text=[text] * len(processed_images),
            padding=True,
            return_tensors="pt"
        ).to(self.device)

        # 生成参数
        gen_kwargs = {"max_new_tokens": max_new_tokens} if max_new_tokens > 0 else {}
        if temperature > 0:
            gen_kwargs["temperature"] = temperature
            gen_kwargs["do_sample"] = True
        if top_p > 0:
            gen_kwargs["top_p"] = top_p

        with torch.no_grad():
            gen_ids = self.model.generate(**inputs, **gen_kwargs)
            gen_ids = [out[len(inp):] for inp, out in zip(inputs.input_ids, gen_ids)]
            captions = self.processor.batch_decode(gen_ids, skip_special_tokens=True,
                                                    clean_up_tokenization_spaces=False)

        if disable_think:
            captions = [re.sub(r'<think>.*?</think>\s*', '', cap, flags=re.DOTALL).strip()
                        for cap in captions]
        return captions

    def unload(self):
        """彻底卸载模型，释放所有资源"""
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
        if hasattr(self, 'processor') and self.processor is not None:
            del self.processor
            self.processor = None

        # 删除所有自定义属性（避免残留引用）
        for attr in list(self.__dict__.keys()):
            if attr not in ['_loaded']:  # 保留 _loaded 以便检查
                try:
                    delattr(self, attr)
                except:
                    pass

        self._loaded = False
        print("[Qwen35ModelWrapper] 模型已彻底卸载")


class LoadQwen35Model:
    """加载 Qwen2.5-VL 模型的节点（纯ModelScope，强制自动卸载旧模型，支持全局清理）"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_name": (MODEL_NAMES, {"default": MODEL_NAMES[0]}),
                "quantization": (["none", "4bit", "8bit"], {"default": "none"}),
                "use_cpu": ("BOOLEAN", {"default": False}),
                "use_flash_attn": ("BOOLEAN", {"default": False}),
                "local_files_only": ("BOOLEAN", {"default": False}),
                "force_clean_before_switch": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "cache_dir": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("QWEN35_MODEL",)
    FUNCTION = "load_model"
    CATEGORY = "ComfyUI-Qwen3.5-Low-VRAM-GPU"

    def load_model(self, model_name, quantization, use_cpu, use_flash_attn,
                   local_files_only, force_clean_before_switch, cache_dir=""):
        global _current_model, _current_model_key

        model_id = MODEL_CONFIG[model_name]

        # 默认缓存路径：ComfyUI/models/Qwen
        if not cache_dir:
            cache_dir = os.path.join(folder_paths.models_dir, "Qwen")
            os.makedirs(cache_dir, exist_ok=True)

        # 构建当前请求的键
        current_key = (model_name, quantization, use_cpu, use_flash_attn)

        # 检查是否已加载相同配置的模型
        if _current_model is not None and _current_model_key == current_key:
            print(f"[LoadQwen35Model] 复用已加载的模型: {model_name} ({quantization})")
            return (_current_model,)

        # 根据 force_clean_before_switch 决定清理范围
        if force_clean_before_switch:
            print("[LoadQwen35Model] 强制清理所有已加载模型...")
            # 卸载 ComfyUI 管理的所有模型（包括其他节点加载的）
            model_management.unload_all_models()
            model_management.cleanup_models()
            # 同时清理我们自己的全局模型
            unload_current_model()
            # 强制垃圾回收和显存清理
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        else:
            # 仅卸载插件自己的模型
            unload_current_model()

        # 通过 ModelScope 获取本地路径（如果 local_files_only=True 且本地不存在，会抛出异常）
        try:
            local_path = download_from_modelscope(
                model_id,
                cache_dir=cache_dir,
                local_files_only=local_files_only
            )
        except Exception as e:
            print(f"[LoadQwen35Model] 获取模型本地路径失败: {e}")
            raise

        # 创建新包装器并加载模型
        wrapper = Qwen35ModelWrapper()
        wrapper.load_model(
            model_path=local_path,
            quant=quantization if quantization != "none" else None,
            use_cpu=use_cpu,
            use_flash_attn=use_flash_attn,
            cache_dir=cache_dir,
            model_name=model_name,
            quant_str=quantization
        )

        # 更新全局缓存
        _current_model = wrapper
        _current_model_key = current_key

        return (wrapper,)


class Qwen35Caption:
    """使用加载的模型生成图像描述（支持推理后卸载）"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("QWEN35_MODEL",),
                "images": ("IMAGE",),
                "system_prompt": ("STRING", {"default": DEFAULT_SYSTEM_PROMPT, "multiline": True}),
                "user_prompt": ("STRING", {"default": DEFAULT_USER_PROMPT, "multiline": True}),
                "temperature": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.1}),
                "top_p": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.1}),
                "max_new_tokens": ("INT", {"default": 1024, "min": 0, "max": 8192}),
                "image_size": ("INT", {"default": 1024, "min": 64, "max": 2048}),
                "disable_think": ("BOOLEAN", {"default": True}),
                "unload_after_caption": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "caption"
    CATEGORY = "ComfyUI-Qwen3.5-Low-VRAM-GPU"

    def caption(self, model, images, system_prompt, user_prompt,
                temperature, top_p, max_new_tokens, image_size, disable_think,
                unload_after_caption):
        # 确保 model 是有效的包装器
        if model is None:
            raise RuntimeError("传入的模型对象为 None，请先执行 LoadQwen35Model 节点加载模型。")

        pil_images = tensor_to_pil(images)
        try:
            captions = model.generate_caption(
                images=pil_images,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                image_size=image_size,
                disable_think=disable_think
            )
        except RuntimeError as e:
            # 捕获模型未加载的异常，给出更友好的提示
            raise RuntimeError(f"生成描述失败：{e} 请检查模型是否已正确加载，或重新执行 LoadQwen35Model 节点。")

        result = "\n".join(captions)

        if unload_after_caption:
            print("[Qwen35Caption] 生成描述后卸载模型")
            model.unload()
            # 如果当前全局模型正是这个，也清空全局缓存
            global _current_model, _current_model_key
            if _current_model is model:
                _current_model = None
                _current_model_key = None
            # 立即清理
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return (result,)


class ShowCaptionText:
    """在 ComfyUI 界面中显示生成的描述文本（前端 JS 增强）"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True, "multiline": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_NODE = True
    FUNCTION = "display"
    CATEGORY = "ComfyUI-Qwen3.5-Low-VRAM-GPU"

    def display(self, text, unique_id=None, extra_pnginfo=None):
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            text = " "
        return {"ui": {"text": [text]}, "result": (text,)}