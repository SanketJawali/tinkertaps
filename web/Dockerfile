# FROM node:26-alpine AS frontend
# WORKDIR /app
# COPY package*.json .
# RUN npm ci
# COPY . .
# RUN npm run build
#
# FROM nginx
# COPY --from=frontend /app/dist /usr/share/nginx/html
# COPY ./nginx.conf /etc/nginx/conf.d/default.conf
# EXPOSE 5000
# CMD ["nginx", "-g", "daemon off;"]
# ========================================================================================
# FROM node:26-alpine AS build
#
# WORKDIR /app
#
# COPY package*.json ./
# RUN npm ci
#
# COPY . .
# RUN npm run build
#
#
# FROM node:26-alpine
#
# WORKDIR /app
#
# COPY --from=build /app/dist ./dist
# COPY --from=build /app/node_modules ./node_modules
# COPY --from=build /app/package.json ./package.json
#
# EXPOSE 4321
#
# CMD ["node", "./dist/server/entry.mjs"]
# =========================================================================================
FROM node:26-alpine AS runtime
WORKDIR /app

COPY . .

RUN npm ci
RUN npm run build

ENV HOST=0.0.0.0
ENV PORT=4321
EXPOSE 4321
CMD ["node", "./dist/server/entry.mjs"]
