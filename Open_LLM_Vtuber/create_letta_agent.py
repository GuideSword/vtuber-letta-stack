from letta_client import Letta

# Create a Letta client instance
client = Letta(base_url="http://localhost:9000")

# Try to create an agent
print("Creating Letta agent...")
try:
    # Try with both LLM and embedding configurations
    agent = client.agents.create(
        name="Open LLM Vtuber Agent",
        llm_config={
            "model": "llama3",
            "model_endpoint": "http://localhost:11434/v1",
            "model_endpoint_type": "ollama",
            "context_window": 8192
        },
        embedding_config={
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_endpoint": "http://localhost:11434/v1",
            "embedding_endpoint_type": "ollama",
            "embedding_dim": 384,
            "embedding_chunk_size": 300
        }
    )
    print(f"Agent created successfully: {agent.id}")
except Exception as e:
    print(f"Error creating agent: {e}")

# List all agents
print("\nListing all agents...")
try:
    agents = client.agents.list()
    print(f"Found {len(agents)} agents:")
    for agent in agents:
        print(f"- {agent.name} (ID: {agent.id})")
except Exception as e:
    print(f"Error listing agents: {e}")
