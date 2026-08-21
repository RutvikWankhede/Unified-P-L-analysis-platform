FROM nginx:alpine

# Copy the static frontend files into the Nginx server directory
COPY . /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
