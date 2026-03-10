import os
import cv2
import numpy as np
from PIL import Image

def image_process(image: Image.Image, target_size: int) -> np.ndarray:
    """将 PIL 图像填充为正方形并缩放到 target_size"""
    image = image.convert('RGBA')
    new = Image.new('RGBA', image.size, 'WHITE')
    new.alpha_composite(image)
    image = new.convert('RGB')

    w, h = image.size
    desired = max(max(w, h), target_size)
    dw, dh = desired - w, desired - h
    top, bottom = dh // 2, dh - (dh // 2)
    left, right = dw // 2, dw - (dw // 2)

    img_arr = np.asarray(image)
    padded = cv2.copyMakeBorder(img_arr, top, bottom, left, right,
                                borderType=cv2.BORDER_CONSTANT, value=[255,255,255])

    if padded.shape[0] > target_size:
        padded = cv2.resize(padded, (target_size, target_size), interpolation=cv2.INTER_AREA)
    elif padded.shape[0] < target_size:
        padded = cv2.resize(padded, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
    return padded

def tensor_to_pil(tensor):
    """将 ComfyUI 的 IMAGE tensor (B,H,W,C) 转换为 PIL 图像列表"""
    images = []
    for i in range(tensor.shape[0]):
        img = tensor[i].cpu().numpy()
        img = (img * 255).astype(np.uint8)
        images.append(Image.fromarray(img))
    return images

def download_from_modelscope(model_id: str, cache_dir: str = None, local_files_only: bool = False) -> str:
    """
    从 ModelScope 下载模型，返回本地路径。
    如果 local_files_only=True，则仅从本地缓存获取，不存在则抛出异常。
    cache_dir 为基础缓存目录，最终模型会存放在 cache_dir/modelscope/<model_id> 下。
    """
    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError:
        raise ImportError("请安装 modelscope: pip install modelscope")

    # 确定最终缓存目录
    if cache_dir:
        model_cache_dir = os.path.join(cache_dir, "modelscope")
        os.makedirs(model_cache_dir, exist_ok=True)
    else:
        model_cache_dir = None

    print(f"[ModelScope] 获取模型 {model_id} 的本地路径 (local_files_only={local_files_only})...")
    local_path = snapshot_download(
        model_id,
        cache_dir=model_cache_dir,
        local_files_only=local_files_only,
        revision='master'
    )
    print(f"[ModelScope] 模型本地路径: {local_path}")
    return local_path