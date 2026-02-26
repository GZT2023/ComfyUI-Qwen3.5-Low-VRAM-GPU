import numpy as np
from PIL import Image
import io
import base64

class QwenVideoPromptReverse:
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "qwen_model": ("QWEN_MODEL",),
                "images": ("IMAGE",),
                "frame_sample_rate": ("INT", {"default": 8, "min": 1, "max": 60, "step": 1}),
                "max_frames": ("INT", {"default": 16, "min": 1, "max": 64, "step": 1}),
                "output_format": (
                    ["Z-Image Turbo", "Z-Image Base", "Qwen Image", "Flux.2 Klein",
                     "Stable Video Diffusion", "Runway Gen-3", "Pika 1.5", "自定义"],
                    {"default": "Stable Video Diffusion"}
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
    RETURN_NAMES = ("prompt", "motion_description", "full_output")
    FUNCTION = "reverse_video_prompt"
    CATEGORY = "Qwen-Low-VRAM"

    def reverse_video_prompt(self, qwen_model, images, frame_sample_rate, max_frames, 
                             output_format, enable_thinking, custom_system_prompt=""):
        
        llm = qwen_model["llm"]
        
        if qwen_model.get("mmproj_path") == "None" or qwen_model.get("mmproj_path") is None:
            return ("错误：未加载多模态投影文件", " ", "错误：未加载多模态投影文件")
        
        total_frames = len(images)
        sample_indices = list(range(0, total_frames, frame_sample_rate))[:max_frames]
        
        content = []
        for idx in sample_indices:
            img_array = images[idx].cpu().numpy()
            if img_array.ndim == 4:
                img_array = img_array[0]
            img_pil = Image.fromarray((img_array * 255).astype(np.uint8))
            buffer = io.BytesIO()
            img_pil.save(buffer, format='JPEG', quality=75)
            b64 = base64.b64encode(buffer.getvalue()).decode()
            
            content.append({
                "type": "image_url",
                "image_url": {"url": f"image/jpeg;base64,{b64}"}
            })
        
        format_tips = {
            "Z-Image Turbo": "输出格式：Z-Image Turbo 视频提示词",
            "Z-Image Base": "输出格式：Z-Image Base 视频提示词",
            "Qwen Image": "输出格式：Qwen Image 视频提示词",
            "Flux.2 Klein": "输出格式：Flux.2 Klein 视频提示词",
            "Stable Video Diffusion": "输出格式：SVD 提示词（motion, camera movement）",
            "Runway Gen-3": "输出格式：Runway Gen-3 提示词",
            "Pika 1.5": "输出格式：Pika 1.5 提示词",
            "自定义": "输出格式：按用户自定义要求"
        }
        
        # ✅ 关键修复：通过 system prompt 控制 thinking
        if custom_system_prompt and custom_system_prompt.strip():
            system_prompt = custom_system_prompt.strip()
        else:
            thinking_hint = "请先逐步思考，再给出答案。\n\n" if enable_thinking else "请直接回答，不要输出思考过程。\n\n"
            system_prompt = f"""{thinking_hint}你是专业的视频提示词工程师。分析提供的视频帧序列，生成视频生成模型的提示词。
{format_tips.get(output_format, "")}
输出结构：
【场景描述】整体内容
【运动描述】动作和变化
【核心提示词】可直接使用
"""
        
        content.append({"type": "text", "text": f"分析了{len(sample_indices)}帧，请生成视频提示词。"})

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
                    {"role": "user", "content": content}
                ],
                **sampling_params  # ✅ 不再包含 chat_template_kwargs
            )

            full_output = response['choices'][0]['message']['content']

            prompt = full_output
            motion_desc = " "

            if "【运动描述】" in full_output:
                motion_desc = full_output.split("【运动描述】")[-1].split("【")[0].strip()

            if "【核心提示词】" in full_output:
                prompt = full_output.split("【核心提示词】")[-1].split("【")[0].strip()

            return (prompt, motion_desc, full_output)

        except Exception as e:
            return (f"错误：{str(e)}", " ", f"错误：{str(e)}")