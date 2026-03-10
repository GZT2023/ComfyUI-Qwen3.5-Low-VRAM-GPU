from .nodes import LoadQwen35Model, Qwen35Caption, ShowCaptionText

NODE_CLASS_MAPPINGS = {
    "LoadQwen35Model (Low VRAM)": LoadQwen35Model,
    "Qwen35Caption (Low VRAM)": Qwen35Caption,
    "ShowCaptionText (Low VRAM)": ShowCaptionText,
}

__all__ = ['NODE_CLASS_MAPPINGS']


WEB_DIRECTORY = "./js"