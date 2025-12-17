# 安装Extended SDK指南

## 问题说明

如果在前端配置Extended交易所时，测试连接失败并提示"Extended SDK未安装"，需要安装Extended交易所的SDK。

## 安装步骤

### 1. 激活虚拟环境

```bash
source venv/bin/activate
```

### 2. 安装Extended SDK

```bash
pip install x10-python-trading-starknet
```

### 3. 验证安装

```bash
pip list | grep x10
```

如果看到 `x10-python-trading-starknet` 说明安装成功。

### 4. 重启服务

安装完成后，需要重启服务：

```bash
# 停止当前服务（如果正在运行）
lsof -ti:8000 | xargs kill -9

# 重新启动服务
source venv/bin/activate
python run.py
```

## 注意事项

1. **SDK依赖**: Extended SDK可能需要额外的系统依赖，如果安装失败，请查看错误信息
2. **Python版本**: 确保Python版本兼容（建议3.8+）
3. **网络连接**: 安装SDK需要网络连接

## 故障排除

### 问题1: pip install失败

**解决方案**: 
- 检查网络连接
- 尝试使用国内镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple x10-python-trading-starknet`

### 问题2: 安装后仍然提示未安装

**解决方案**:
- 确认已激活正确的虚拟环境
- 检查是否在项目目录下
- 重启服务

### 问题3: 导入错误

**解决方案**:
- 检查 `jiaoyisuoshili/extended.py` 文件是否存在
- 确认SDK版本兼容性

## 测试

安装完成后，在前端界面：
1. 选择Extended交易所
2. 填写配置信息
3. 点击"测试连接"
4. 应该能看到连接成功的提示

