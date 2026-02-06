# 1. 使用官方 Node.js 轻量级镜像作为基础
FROM node:20-alpine AS builder

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖定义文件
COPY package*.json ./

# 4. 安装依赖
RUN npm install

# 5. 复制所有项目文件
COPY . .

# 6. 执行构建 (生成 .next 文件夹)
RUN npm run build

# --- 运行阶段 ---
FROM node:20-alpine AS runner
WORKDIR /app

# 7. 设置环境变量为生产模式
ENV NODE_ENV=production

# 8. 从构建阶段复制必要文件
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

# 9. 暴露端口
EXPOSE 3000

# 10. 启动 Next.js 服务
CMD ["npm", "start"]