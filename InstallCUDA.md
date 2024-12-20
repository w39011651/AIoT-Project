# 解決跑模型幀數太低的方法
## 為NVIDIA GPU安裝CUDA
* CUDA(Opt)
* Pytorch

----
## 前置作業
首先，先確認顯示卡是否支援CUDA
在powershell/cmd中輸入
```
nvidia-smi
```
輸入完畢後，應該會看到顯示卡支援的CUDA版本

---

## CUDA(Opt)
詳情可參考這篇文章[CSDN](https://blog.csdn.net/bja20040205/article/details/135970465)
到[NVIDIA官網](https://developer.nvidia.com/cuda-toolkit-archive)下載有支援的CUDA版本

---

## Pytorch
詳情可參考這篇文章[CSDN](https://blog.csdn.net/Luobinhai/article/details/140216028?utm_medium=distribute.pc_relevant.none-task-blog-2~default~baidujs_baidulandingword~default-4-140216028-blog-135139310.235^v43^pc_blog_bottom_relevance_base2&spm=1001.2101.3001.4242.3&utm_relevant_index=7)

先到[Pytorch官網](https://pytorch.org/get-started/locally/)

然後<font color = 'red'>先不要下載</font>
找到[Previous Pytorch Version](https://pytorch.org/get-started/previous-versions/)，選擇版本(如v.2.5.0)
然後看到適合到CUDA版本
```
# CUDA 12.1
pip install torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 --index-url https://download.pytorch.org/whl/cu121
```

記住torch,torchvision和torchaudio的版本
然後前往[--index-url](https://download.pytorch.org/whl/cu121)後下載對應的torch,torchvision和torchaudio


安裝完畢後可以在 powershell/cmd 中輸入:
```
pip install 剛剛那三個檔案的路徑
```

最後在 powershell 檢查有沒有被正確安裝:
```
python
>>>import torch
>>>
>>>print(torch.__version__)
2.5.0+cu121
>>>print(torch.cuda.is_available())
1
>>>print(torch.version.cuda)
12.1
```
如果是低於python 3.10的版本可以輸入:
```
yolo task=detect mode=predict conf=0.25 model=yolov8n.pt source='ultralytics/assets/bus.jpg'
```
檢查
如果是python 3.10以上會出現Import Error

---

## 結語
### 我裝了這些東西花了我兩個小時，謝謝你Pytorch，謝謝你NVIDIA