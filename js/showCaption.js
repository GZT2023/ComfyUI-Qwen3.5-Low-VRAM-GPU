import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

app.registerExtension({
    name: "Qwen3.5.ShowCaption",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ShowCaptionText (Low VRAM)") {

            function createTextWidgets(node, texts) {
                // 移除旧的文本 widgets（保留可能的输入 widget）
                if (node.widgets) {
                    const startIdx = node.inputs && node.inputs[0] && node.inputs[0].widget ? 1 : 0;
                    for (let i = startIdx; i < node.widgets.length; i++) {
                        node.widgets[i].onRemove?.();
                    }
                    node.widgets.length = startIdx;
                }

                if (!Array.isArray(texts)) texts = [texts];

                for (const t of texts) {
                    if (t === undefined || t === null) continue;
                    const str = String(t);
                    const w = ComfyWidgets["STRING"](node, "caption_" + (node.widgets?.length ?? 0), ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    
                    // 关键修改：使用主题变量，适应深色/浅色主题
                    w.inputEl.style.background = "transparent";
                    w.inputEl.style.color = "var(--input-text, var(--fg-color))";
                    w.inputEl.style.border = "none";
                    w.inputEl.style.outline = "none";
                    w.inputEl.style.padding = "2px 4px";
                    w.inputEl.style.fontFamily = "inherit";
                    w.inputEl.style.fontSize = "inherit";
                    
                    w.value = str;
                }

                // 调整节点大小以适应内容
                requestAnimationFrame(() => {
                    const size = node.computeSize();
                    if (size[0] < node.size[0]) size[0] = node.size[0];
                    if (size[1] < node.size[1]) size[1] = node.size[1];
                    node.onResize?.(size);
                    app.graph.setDirtyCanvas(true, false);
                });
            }

            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                if (message?.text) {
                    createTextWidgets(this, message.text);
                }
            };

            const VALUES = Symbol("savedTexts");
            const configure = nodeType.prototype.configure;
            nodeType.prototype.configure = function () {
                this[VALUES] = arguments[0]?.widgets_values;
                return configure?.apply(this, arguments);
            };

            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                onConfigure?.apply(this, arguments);
                const saved = this[VALUES];
                if (saved?.length) {
                    const startIdx = this.inputs && this.inputs[0] && this.inputs[0].widget ? 1 : 0;
                    const texts = saved.slice(startIdx);
                    if (texts.length) {
                        requestAnimationFrame(() => {
                            createTextWidgets(this, texts);
                        });
                    }
                }
            };
        }
    }
});