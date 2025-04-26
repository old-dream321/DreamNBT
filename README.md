# DreamNBT
一个Minecraft基岩版NBT解析工具

## 安装
```shell
pip install DreamNBT
```

## 使用
### 1.读取NBT文件
```python
from DreamNBT import parse_binary
with open("test.dat", "rb") as f:
    nbt = parse_binary(f)
```
### 2.格式化输出NBT
```python
print(nbt)
```
示例输出:
```text
TAG_Compound(): 3 entries {
  TAG_Int(t1): 23455
  TAG_List(t2): 3 entries [
    TAG_Int(): 1
    TAG_Int(): 2
    TAG_Int(): 3
  ]
  TAG_Compound(t3): 2 entries {
    TAG_Byte(aa): 1
    TAG_Compound(t4): 2 entries {
      TAG_Int(t1): 23455
      TAG_List(t2): 3 entries [
        TAG_Int(): 1
        TAG_Int(): 2
        TAG_Int(): 3
      ]
    }
  }
}
```
### 3.构建和修改NBT
示例：构建上面输出的NBT
```python
from DreamNBT import *

a = TAG_Compound()

a["t1"] = TAG_Int(23455)

a["t2"] = TAG_List([TAG_Int(1), TAG_Int(2), TAG_Int(3)])

a["t3"] = TAG_Compound()
a["t3"]["aa"] = TAG_Byte(1)

b = TAG_Compound()
b["t1"] = TAG_Int(23455)
b["t2"] = TAG_List([TAG_Int(1), TAG_Int(2), TAG_Int(3)])
a["t3"]["t4"] = b
```
### 4.NBT转为二进制
```python
with open("test.dat", "wb") as f:
    f.write(a.to_binary())
```
### 5.SNBT解析
```python
from DreamNBT import parse_snbt
nbt = parse_snbt("{t1:23455,t2:[1,2,3],t3:{aa:1,t4:{t1:23455,t2:[1,2,3]}}}")
```
### 6.NBT转为SNBT
```python
print(nbt.to_snbt())
```
示例输出:
```text
{t1:23455,t2:[1,2,3],t3:{aa:1,t4:{t1:23455,t2:[1,2,3]}}}
```
