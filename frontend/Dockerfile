# Optional: deploy the React app as a second Railway service
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_DEMO_STUDENT_ID=student-001
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_DEMO_STUDENT_ID=$VITE_DEMO_STUDENT_ID
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
