FROM elasticsearch:7.17.5

# Install plugins
RUN /usr/share/elasticsearch/bin/elasticsearch-plugin install analysis-icu && \
    /usr/share/elasticsearch/bin/elasticsearch-plugin install analysis-kuromoji

# Copy entrypoint script để tự động setup keystore
COPY docker-entrypoint.sh /usr/local/bin/custom-entrypoint.sh
RUN chmod +x /usr/local/bin/custom-entrypoint.sh

# Override entrypoint
ENTRYPOINT ["/usr/local/bin/custom-entrypoint.sh"]
