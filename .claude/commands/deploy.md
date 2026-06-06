Deploy the VERSE MCP server with a full rebuild:
1. cd /home/glados/deployments/verse-mcp
2. DOCKER_HOST=unix:///run/user/988/docker.sock docker compose down
3. DOCKER_HOST=unix:///run/user/988/docker.sock docker compose build --no-cache verse-mcp
4. DOCKER_HOST=unix:///run/user/988/docker.sock docker compose up -d
5. Verify: DOCKER_HOST=unix:///run/user/988/docker.sock docker logs verse-mcp --tail 20
