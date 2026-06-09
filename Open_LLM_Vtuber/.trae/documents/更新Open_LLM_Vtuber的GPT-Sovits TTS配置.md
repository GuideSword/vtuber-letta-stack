# 更新Open_LLM_Vtuber的GPT-Sovits TTS配置计划

## 分析现状
- Open_LLM_Vtuber已配置使用GPT-Sovits TTS，端口设置为12345
- 当前配置缺少MoeChat实现中的一些高级参数
- 需要更新配置以支持更多GPT-Sovits特性

## 更新步骤

### 1. 更新GPT-Sovits配置参数
在`conf.yaml`文件的`gpt_sovits_tts`部分添加/修改以下参数：
- 添加`seed`参数（默认-1）
- 添加`top_k`参数（默认15）
- 调整`batch_size`参数值（从'1'改为'20'）
- 确保`text_lang`和`prompt_lang`保持为'zh'

### 2. 验证配置结构
- 确保配置结构与MoeChat的实现保持一致
- 验证API URL端口是否正确设置为12345
- 检查所有必需参数是否存在

### 3. 检查配置文件语法
- 确保修改后的YAML文件语法正确
- 验证缩进和格式是否符合规范

## 预期结果
- Open_LLM_Vtuber的GPT-Sovits TTS配置将与MoeChat的实现保持一致
- 支持更多高级参数，如seed和top_k
- 能够正确连接到运行在端口12345上的GPT-Sovits服务