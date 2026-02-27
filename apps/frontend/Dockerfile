FROM node:20-alpine AS base
WORKDIR /app
COPY package.json /app/
RUN npm install
COPY . /app

FROM base AS dev
CMD ["npm", "run", "dev"]

FROM base AS build
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

