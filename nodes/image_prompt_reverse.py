import numpy as np
from PIL import Image
import io
import base64

class QwenImagePromptReverse:
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "qwen_model": ("QWEN_MODEL",),
                "image": ("IMAGE",),
                "output_format": (
                    ["Z-Image Turbo", "Z-Image Base", "Qwen Image", "Flux.2 Klein", 
                     "Stable Diffusion XL", "Midjourney V6", "DALL-E 3", "Flux.1", "自定义"],
                    {"default": "Z-Image Turbo"}
                ),
                "detail_level": (
                    ["简洁", "标准", "详细", "超详细"],
                    {"default": "详细"}
                ),
                "enable_thinking": ("BOOLEAN", {"default": True}),
                "custom_system_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "可选：自定义系统提示词（留空使用默认）"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "analysis", "full_output")
    FUNCTION = "reverse_prompt"
    CATEGORY = "Qwen-Low-VRAM"

    def reverse_prompt(self, qwen_model, image, output_format, detail_level, 
                       enable_thinking, custom_system_prompt=""):
        
        llm = qwen_model["llm"]
        
        if qwen_model.get("mmproj_path") == "None" or qwen_model.get("mmproj_path") is None:
            return ("错误：未加载多模态投影文件", " ", "错误：未加载多模态投影文件")
        
        # 转换图像（修复维度问题）
        img_array = image.cpu().numpy()
        if img_array.ndim == 4:
            img_array = img_array[0]
        if img_array.ndim == 3 and img_array.shape[0] == 1:
            img_array = img_array[0]

        img_pil = Image.fromarray((img_array * 255).astype(np.uint8))
        
        buffer = io.BytesIO()
        img_pil.save(buffer, format='JPEG', quality=85)
        b64 = base64.b64encode(buffer.getvalue()).decode()
        
        detail_map = {
            "简洁": "用 50 字以内简洁描述",
            "标准": "用 100-150 字详细描述",
            "详细": "用 200-300 字非常详细地描述",
            "超详细": "用 400 字以上极其详细地描述"
        }
        
        format_tips = {
            "Z-Image Turbo": "输出格式：Z-Image Turbo 优化提示词（强调光影、构图、细节）",
            "Z-Image Base": "输出格式：Z-Image Base 标准提示词",
            "Qwen Image": "输出格式：Qwen Image 原生提示词格式",
            "Flux.2 Klein": "输出格式：Flux.2 Klein 提示词（强调艺术风格、色彩）",
            "Stable Diffusion XL": "输出格式：SDXL 提示词（subject, style, quality tags）",
            "Midjourney V6": "输出格式：Midjourney V6 提示词（--ar --v 6.0 参数）",
            "DALL-E 3": "输出格式：DALL-E 3 自然语言描述",
            "Flux.1": "输出格式：Flux.1 提示词",
            "自定义": "输出格式：按用户自定义要求"
        }
        
        # ✅ 关键修复：通过 system prompt 控制 thinking，移除 chat_template_kwargs
        if custom_system_prompt and custom_system_prompt.strip():
            system_prompt = custom_system_prompt.strip()
        else:
            thinking_hint = "请先逐步思考，再给出答案。\n\n" if enable_thinking else "请直接回答，不要输出思考过程。\n\n"
            system_prompt = f"""{thinking_hint}你是专业的 AI 绘画提示词工程师。分析提供的图片，生成可用于 AI 绘画的提示词。
{format_tips.get(output_format, "")}
详细程度：{detail_map[detail_level]}
输出结构：
【画面分析】详细描述画面内容
【核心提示词】可直接用于 AI 绘画的英文提示词
"""
        
        user_content = [
            {"type": "image_url", "image_url": {"url": f"image/jpeg;base64,{b64}"}},
            {"type": "text", "text": "请分析这张图片，生成 AI 绘画提示词。"}
        ]

        # ✅ 采样参数（已移除 chat_template_kwargs）
        sampling_params = {
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
        }

        try:
            response = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                **sampling_params  # ✅ 不再包含 chat_template_kwargs
            )

            full_output = response['choices'][0]['message']['content']

            prompt = full_output
            analysis = " "

            if "【画面分析】" in full_output:
                analysis = full_output.split("【画面分析】")[-1].split("【核心提示词】")[0].strip()

            if "【核心提示词】" in full_output:
                prompt = full_output.split("【核心提示词】")[-1].strip()

            return (prompt, analysis, full_output)

        except Exception as e:
            return (f"错误：{str(e)}", " ", f"错误：{str(e)}")