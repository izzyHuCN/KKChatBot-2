# Dify端口映射解决方案

## 问题分析
你的Dify服务运行在Docker容器中，但5001端口没有映射到主机，导致外部应用无法访问。

## 解决方案步骤

### 方法1：重新创建Dify容器并映射端口

1. 首先停止当前的Dify容器：
```bash
docker stop docker-api-1 docker-web-1
docker rm docker-api-1 docker-web-1
```

2. 重新创建容器并映射端口：
```bash
docker run -d --name dify-api -p 5001:5001 langgenius/dify-api:1.11.4
docker run -d --name dify-web -p 3000:3000 langgenius/dify-web:1.11.4
```

### 方法2：修改现有容器（推荐）

1. 提交当前容器为镜像：
```bash
docker commit docker-api-1 dify-api-new
docker commit docker-web-1 dify-web-new
```

2. 停止旧容器：
```bash
docker stop docker-api-1 docker-web-1
docker rm docker-api-1 docker-web-1
```

3. 重新创建带端口映射的容器：
```bash
docker run -d --name dify-api -p 5001:5001 dify-api-new
docker run -d --name dify-web -p 3000:3000 dify-web-new
```

### 方法3：使用Docker Compose（最推荐）

创建一个新的 `docker-compose.override.yml` 文件：

```yaml
version: '3.8'
services:
  api:
    ports:
      - "5001:5001"
  web:
    ports:
      - "3000:3000"
```

然后运行：
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

## 验证连接

完成端口映射后，测试连接：
```bash
curl http://localhost:5001/v1/chat-messages -H "Authorization: Bearer app-DJRsIxTBbLz5pkazjcjSkG20" -H "Content-Type: application/json" -d '{"inputs":{},"query":"Hello","response_mode":"streaming","conversation_id":"","user":"test-user"}'
```

## 预期结果
如果连接成功，你应该能看到Dify返回的流式响应数据。