"""
Social Manager Skill - LinkedIn Post Drafting (HITL)
=====================================================

Human-in-the-Loop Implementation:
- This skill NEVER posts directly to LinkedIn
- Drafts are saved to vault/Inbox/ for human review
- Human moves approved posts to vault/Approved/
- main.py monitors Approved/ and handles posting

Workflow:
1. AI generates draft -> vault/Inbox/
2. Human reviews and edits
3. Human moves to vault/Approved/
4. main.py posts to LinkedIn and moves to vault/Done/
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VAULT_DIR = PROJECT_ROOT / "vault"
INBOX_DIR = VAULT_DIR / "Inbox"  # Changed from Drafts - HITL workflow


def ensure_directories():
    """Ensure required directories exist."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    (VAULT_DIR / "Approved").mkdir(parents=True, exist_ok=True)
    (VAULT_DIR / "Done").mkdir(parents=True, exist_ok=True)


def draft_linkedin_post(topic: str, tone: str = "professional", length: str = "medium") -> dict:
    """
    Draft a LinkedIn post using OpenAI API.

    IMPORTANT: This function NEVER posts to LinkedIn directly.
    It only saves drafts to vault/Inbox/ for human review.

    Args:
        topic: The subject matter for the post
        tone: Writing style (professional, casual, inspirational)
        length: Post length (short, medium, long)

    Returns:
        dict with 'success', 'content', and 'file_path' keys
    """
    ensure_directories()

    if not OPENAI_API_KEY:
        return {
            "success": False,
            "error": "OPENAI_API_KEY not found in .env",
            "content": None,
            "file_path": None
        }

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        length_guide = {
            "short": "2-3 sentences",
            "medium": "1 paragraph (4-6 sentences)",
            "long": "2-3 paragraphs"
        }

        prompt = f"""Write a LinkedIn post about: {topic}

Tone: {tone}
Length: {length_guide.get(length, length_guide['medium'])}

Guidelines:
- Start with a hook that grabs attention
- Include relevant insights or value
- End with a call-to-action or thought-provoking question
- Use line breaks for readability
- Include 3-5 relevant hashtags at the end

IMPORTANT: Return ONLY the post content, no additional commentary.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a LinkedIn content strategist who creates engaging, professional posts. Return only the post content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        post_content = response.choices[0].message.content

        # Save to vault/Inbox for human review (HITL)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = re.sub(r'[<>:"/\\|?*]', '', topic)[:30].replace(' ', '_')
        filename = f"LinkedIn_Draft_{timestamp}_{safe_topic}.md"
        file_path = INBOX_DIR / filename

        markdown_content = f"""# LinkedIn Post Draft

**Topic:** {topic}
**Tone:** {tone}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Status:** Pending Human Review

---

## Post Content

{post_content}

---

## HITL Instructions

1. Review the content above
2. Edit directly in this file if needed
3. When approved, move this file to `vault/Approved/`
4. The AI will automatically post it and move to `vault/Done/`

**WARNING:** Do NOT manually post this. The system handles posting automatically.
"""

        file_path.write_text(markdown_content, encoding="utf-8")

        return {
            "success": True,
            "content": post_content,
            "file_path": str(file_path),
            "status": "saved_to_inbox",
            "next_step": "Move to vault/Approved/ after review",
            "error": None
        }

    except ImportError:
        return {
            "success": False,
            "error": "openai package not installed. Run: pip install openai",
            "content": None,
            "file_path": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": None,
            "file_path": None
        }


def extract_post_content(file_path: Path) -> str:
    """
    Extract the actual post content from a draft markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        The extracted post content, cleaned for LinkedIn
    """
    content = file_path.read_text(encoding="utf-8")

    # Try to extract content between "## Post Content" and the next "---"
    match = re.search(r'## Post Content\s*\n\n(.*?)\n\n---', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: try to find content between first --- and second ---
    parts = content.split('---')
    if len(parts) >= 2:
        # The post content is usually in the second section
        post_section = parts[1].strip()
        # Remove metadata lines
        lines = post_section.split('\n')
        content_lines = []
        in_content = False
        for line in lines:
            if line.startswith('## Post Content'):
                in_content = True
                continue
            if in_content and not line.startswith('**'):
                content_lines.append(line)
        if content_lines:
            return '\n'.join(content_lines).strip()

    # Last resort: return everything after the metadata
    lines = content.split('\n')
    content_start = False
    result_lines = []
    for line in lines:
        if '---' in line:
            content_start = True
            continue
        if content_start and not line.startswith('#') and not line.startswith('**'):
            result_lines.append(line)

    return '\n'.join(result_lines).strip()


def get_post_ideas(industry: str = "technology", count: int = 5) -> dict:
    """
    Generate LinkedIn post ideas for a given industry.

    Args:
        industry: The industry/field for post ideas
        count: Number of ideas to generate

    Returns:
        dict with 'success', 'ideas', and optional 'error' keys
    """
    if not OPENAI_API_KEY:
        return {
            "success": False,
            "error": "OPENAI_API_KEY not found in .env",
            "ideas": None
        }

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a LinkedIn content strategist."},
                {"role": "user", "content": f"Generate {count} engaging LinkedIn post ideas for someone in the {industry} industry. Format as a numbered list with brief descriptions."}
            ],
            max_tokens=400,
            temperature=0.8
        )

        ideas = response.choices[0].message.content

        return {
            "success": True,
            "ideas": ideas,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ideas": None
        }


def run_skill(action: str = "draft", **kwargs) -> dict:
    """
    Main entry point for the social manager skill.

    Args:
        action: "draft" or "ideas"
        **kwargs: Additional arguments for the action

    Returns:
        Result dictionary from the action
    """
    if action == "draft":
        topic = kwargs.get("topic", "productivity tips for professionals")
        tone = kwargs.get("tone", "professional")
        length = kwargs.get("length", "medium")
        return draft_linkedin_post(topic, tone, length)

    elif action == "ideas":
        industry = kwargs.get("industry", "technology")
        count = kwargs.get("count", 5)
        return get_post_ideas(industry, count)

    else:
        return {
            "success": False,
            "error": f"Unknown action: {action}. Use 'draft' or 'ideas'."
        }


if __name__ == "__main__":
    # Example usage
    print("=== Social Manager Skill (HITL Mode) ===\n")
    print("This skill NEVER posts directly to LinkedIn.")
    print("Drafts are saved to vault/Inbox/ for human review.\n")

    # Test drafting a post
    result = draft_linkedin_post(
        topic="The importance of continuous learning in tech",
        tone="inspirational",
        length="medium"
    )

    if result["success"]:
        print(f"Draft created successfully!")
        print(f"Saved to: {result['file_path']}")
        print(f"Next step: {result['next_step']}")
        print(f"\nContent preview:\n{result['content'][:200]}...")
    else:
        print(f"Error: {result['error']}")
