将excle格式的小说转为剪映草稿

一、安装剪映
  将JianyingPro Drafts文件夹路径写到同目录的drafts_folder.txt里，例如：E:\JianyingPro Drafts
二、本地部署秋叶整合包
  https://space.bilibili.com/12566101  B站自行学习SD整合包的部署。
  使用时A绘世启动器点击一键启动
  不要关闭控制台！
三、本地部署AI大模型（Ollama+通义千问）
1、下载Ollama
  打开官网：https://ollama.com/
2、安装Ollama
  运行“OllamaSetup.exe”，默认安装在C盘，如果需要把下载AI模型的路径改为D盘
  增加系统变量  
  变量名：OLLAMA_MODELS  
  变量值： D:\ollama\models
3、下载通义千问大模型
  打开“记事本”，复制下行代码，另存为“qwen2.5_7b.bat”文件。
  ollama run qwen2.5:7b
  以后需要运行通义千问，双击运行刚才保存的bat文件即可。当然也可以每次在命令行直接运行命令来启用。
  ollama list  查看本地AI大模型列表
  不要关闭控制台！

四、本地部署GPT-SoVITS-WebUI
  参考https://github.com/RVC-Boss/GPT-SoVITS/blob/main/docs/cn/README.md
  下载下载整合包，解压后双击 go-webui.bat 即可启动 GPT-SoVITS-WebUI。
  不要关闭控制台！
  依次点击“1-GPT-SOVITS-TTS”、“1C推理” 页签
  勾选“启用并行推理版本(推理速度更快)” 点击“开启TTS推理webul”按钮
  不要关闭控制台！

