# 将excle格式的小说转为剪映草稿
## 一、安装剪映
  将JianyingPro Drafts文件夹路径写到同目录的drafts_folder.txt里，例如：E:\JianyingPro Drafts

## 二、本地部署秋叶整合包
  https://space.bilibili.com/12566101  B站自行学习SD整合包的部署。
  使用时A绘世启动器点击一键启动

## 三、本地部署AI大模型（Ollama+通义千问）
### 1、下载Ollama
  打开官网：https://ollama.com/
### 2、安装Ollama
  运行“OllamaSetup.exe”，默认安装在C盘，如果需要把下载AI模型的路径改为D盘
  增加系统变量  
  变量名：OLLAMA_MODELS  
  变量值： D:\ollama\models
### 3、下载通义千问大模型
  打开“记事本”，复制下行代码，另存为“qwen2.5_7b.bat”文件。
  ollama run qwen2.5:7b
  以后需要运行通义千问，双击运行刚才保存的bat文件即可。当然也可以每次在命令行直接运行命令来启用。
  ollama list  查看本地AI大模型列表

## 四、本地部署GPT-SoVITS-WebUI

  参考https://github.com/RVC-Boss/GPT-SoVITS/blob/main/docs/cn/README.md
  下载下载整合包，解压后双击 go-webui.bat 即可启动 GPT-SoVITS-WebUI。

## 五、使用本工具
### 1、配置
    1.1 将JianyingPro Drafts文件夹路径写到同目录的drafts_folder.txt里
    1.2 如果使用chatgpt进行文字处理，将密钥填写进同目录的openai_api_key.txt；如果使用本地通义千问大模型可不填写
    1.3 如果使用远程服务器的SD进行图像处理，将服务地址填写进同目录的webui_server_url.txt 例如 http://region-3.seetacloud.com:32597；如果使用本地秋叶整合包部署的SD可不填写
### 2、处理小说文件
    新建excle文件，随便写一个列标题，比如“第一列” 。复制小说内容，粘贴到excle文件中的“第一列”下，进行分段
### 3、准备工作

下载参考音频 : http://doglast.yaozhiyuan.cn/%E5%8F%82%E8%80%83%E9%9F%B3%E9%A2%91/01%E5%A5%B3%E9%9F%B3%E5%8F%82%E8%80%83/01%E5%A5%B3%E9%9F%B3%E5%8F%82%E8%80%83.WAV
下载参考音频文字 : http://doglast.yaozhiyuan.cn/%E5%8F%82%E8%80%83%E9%9F%B3%E9%A2%91/01%E5%A5%B3%E9%9F%B3%E5%8F%82%E8%80%83/01%E5%A5%B3%E9%9F%B3%E5%8F%82%E8%80%83.txt
    （如果使用pyttsx3生成音频可不下载！）
    A绘世启动器点击一键启动运行 （不要关闭控制台！）
    双击qwen2.5_7b.bat（不要关闭控制台！）
    双击 GPT-SoVITS-v2-240821文件夹下的 go-webui.bat ，依次点击“1-GPT-SOVITS-TTS”、“1C推理” 页签，
    勾选“启用并行推理版本(推理速度更快)” 点击“开启TTS推理webul”按钮（不要关闭控制台！）

### 4、运行本工具
    按需切换业务界面
    例如生成抖音的ai漫画：
    按需切换文字模型（本地的通义千问 或者 chatgpt ）
    按需切换音频模型 （pyttsx3 或者 gpt_sovits）
    区别：pyttsx3就是生成windows自带的机器音 ，gpt_sovits通过参考音频生成克隆音
    例如选择gpt_sovits 然后选择下载参考音频wav文件和下载的参考音频文字txt文件
    然后选择要处理的文件（第2步的excle文件）
    选择包含小说内容的那一列
    最后点击按钮“处理文件”
### 5、耐心等待处理完文件，打开剪映对草稿进行编辑




    
