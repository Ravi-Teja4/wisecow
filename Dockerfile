FROM ubuntu:22.04

# Install required packages
RUN apt-get update && \
    apt-get install -y bash curl coreutils fortune-mod cowsay netcat-openbsd && \
    apt-get clean

# Copy app files
WORKDIR /app
COPY wisecow.sh /app/wisecow.sh
RUN chmod +x /app/wisecow.sh

# Expose port
EXPOSE 4499

# Run the application
CMD ["bash", "/app/wisecow.sh"]

