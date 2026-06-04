"""Example evaluation script for MCP server."""

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional
from verse_mcp.server import mcp  # Assuming we can import the mcp instance

@dataclass
class QATuple:
    question: str
    expected_answer_contains: str
    category: Optional[str] = None

async def run_evaluation(qa_list: List[QATuple]) -> bool:
    """Run a list of Q&A evaluations against the MCP server."""
    all_passed = True
    for qa in qa_list:
        # In a real implementation, we would call the MCP tool via the client.
        # For now, we simulate.
        print(f"Evaluating: {qa.question}")
        # Simulate calling sc_ask tool
        # result = await mcp.call_tool("sc_ask", {"question": qa.question, ...})
        # For placeholder, we just print.
        print("  -> [SIMULATED] Answer received")
        # Check if expected string is in the answer (simulated)
        if qa.expected_answer_contains not in "SIMULATED ANSWER":
            print(f"  -> FAIL: Expected '{qa.expected_answer_contains}' not in answer")
            all_passed = False
        else:
            print("  -> PASS")
    return all_passed

def create_example_xml() -> str:
    """Create an example evaluation XML file."""
    root = ET.Element("evaluations")
    qa_set = ET.SubElement(root, "qa_set")
    qa_set.set("name", "Star Citizen Basics")
    
    qa1 = ET.SubElement(qa_set, "qa")
    qa1.set("question", "What is the maximum speed of the Drake Cutlass Black?")
    qa1.set("expected_contains", "320 m/s")
    qa1.set("category", "ships")
    
    qa2 = ET.SubElement(qa_set, "qa")
    qa2.set("question", "How do I start mining in Star Citizen?")
    qa2.set("expected_contains", "equip a mining laser")
    qa2.set("category", "guide")
    
    tree = ET.ElementTree(root)
    # We'll return the string representation for now
    ET.indent(tree, space="  ", level=0)
    return ET.tostring(root, encoding='unicode')

if __name__ == "__main__":
    print("Example evaluation XML:")
    print(create_example_xml())