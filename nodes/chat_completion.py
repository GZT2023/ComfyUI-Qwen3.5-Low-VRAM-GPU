class QwenChatCompletion:
    """
    Qwen3.0/3.5 文本生成节点
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "qwen_model": ("QWEN_MODEL",),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "你好，请帮我写一个 Python 快速排序函数"
                }),
                "max_tokens": ("INT", {
                    "default": 4096,
                    "min": 1,
                    "max": 32768,
                    "step": 1
                }),
                "temperature": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1
                }),
                "top_p": ("FLOAT", {
                    "default": 0.9,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05
                }),
                "top_k": ("INT", {
                    "default": 20,
                    "min": 1,
                    "max": 100,
                    "step": 1
                }),
                "presence_penalty": ("FLOAT", {
                    "default": 1.5,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1
                }),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 2147483647,
                    "step": 1
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response", "thinking_process", "full_output")
    FUNCTION = "generate"
    CATEGORY = "Qwen-Low-VRAM"

    def generate(self, qwen_model, prompt, max_tokens, temperature, 
                 top_p, top_k, presence_penalty, seed=-1):
        
        llm = qwen_model["llm"]
        enable_thinking = qwen_model["enable_thinking"]
        
        if seed != -1:
            import random
            random.seed(seed)
        
        # 构建采样参数（✅ 已移除 chat_template_kwargs）
        sampling_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "presence_penalty": presence_penalty,
        }
        
        # ✅ 关键修复：通过 system prompt 控制 thinking 模式，而非 chat_template_kwargs
        system_prefix = ""
        if enable_thinking:
            system_prefix = "请先逐步思考，再给出答案。\n\n"
        else:
            system_prefix = "请直接回答问题，不要输出思考过程。\n\n"
        
        try:
            response = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prefix},
                    {"role": "user", "content": prompt}
                ],
                **sampling_params  # ✅ 不再包含 chat_template_kwargs
            )
            
            full_content = response['choices'][0]['message']['content']
            
            # 解析思考内容（兼容模型自发输出的<think>标签）
            thinking = " "
            answer = full_content
            
            if "<think>" in full_content and "</think>" in full_content:
                start = full_content.find("<think>") + len("<think>")
                end = full_content.find("</think>")
                thinking = full_content[start:end].strip()
                answer = full_content[end + len("</think>"):].strip()
            elif not enable_thinking:
                answer = full_content
            
            print(f"[Qwen-Low-VRAM] ✓ 生成完成")
            return (answer, thinking, full_content)
            
        except Exception as e:
            error_msg = f"生成错误：{str(e)}"
            print(f"[Qwen-Low-VRAM] ✗ {error_msg}")
            return (error_msg, " ", error_msg)