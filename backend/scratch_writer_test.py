import asyncio
import logging
from app.agents.writer import writer_node

logging.basicConfig(level=logging.INFO)

async def main():
    state = {
        "subtopics": ["AI in diagnosis"],
        "verified_sources": [
            {
                "title": "Source 1",
                "url": "http://example.com",
                "content": "AI is used in diagnosis."
            }
        ],
        "topic": "Impact of AI",
        "project_id": ""
    }
    try:
        result = await writer_node(state)
        print("Result:", result)
    except Exception as e:
        print("EXCEPTION:", e)

if __name__ == "__main__":
    asyncio.run(main())
