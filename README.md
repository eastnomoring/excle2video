将excle格式的小说转为剪映草稿
需要安装剪映、秋叶整合包、Ollama

本地部署AI大模型（Ollama+通义千问）
一、下载Ollama
打开官网：https://ollama.com/
二、安装Ollama
运行“OllamaSetup.exe”，默认安装在C盘，如果需要把下载AI模型的路径改为D盘
增加系统变量  
变量名：OLLAMA_MODELS  
变量值： D:\ollama\models
三、下载通义千问大模型
打开“记事本”，复制下行代码，另存为“qwen2.5_7b.bat”文件。
ollama run qwen2.5:7b
以后需要运行通义千问，双击运行刚才保存的bat文件即可。当然也可以每次在命令行直接运行命令来启用。

ollama list  查看本地AI大模型列表
