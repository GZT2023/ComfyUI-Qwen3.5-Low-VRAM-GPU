from .nodes.model_loader import QwenModelLoader
from .nodes.chat_completion import QwenChatCompletion
from .nodes.image_prompt_reverse import QwenImagePromptReverse
from .nodes.video_prompt_reverse import QwenVideoPromptReverse

NODE_CLASS_MAPPINGS = {
    "QwenModelLoader": QwenModelLoader,
    "QwenChatCompletion": QwenChatCompletion,
    "QwenImagePromptReverse": QwenImagePromptReverse,
    "QwenVideoPromptReverse": QwenVideoPromptReverse,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QwenModelLoader": "🤖 Qwen 模型加载器 (3.0/3.5)",
    "QwenChatCompletion": "💬 Qwen 文本生成",
    "QwenImagePromptReverse": "🖼️ Qwen 图片提示词反推",
    "QwenVideoPromptReverse": "🎬 Qwen 视频提示词反推",
}

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

print("[Qwen-Low-VRAM] ✓ 插件加载成功")