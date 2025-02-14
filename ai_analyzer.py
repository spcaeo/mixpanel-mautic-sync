# ai_analyzer.py

import json
import openai
from dotenv import load_dotenv
from openai import OpenAIError
from ask_ai import AskAIClient, AIModel

load_dotenv()

class AIAnalyzer:
    def __init__(self, config_path="openai_config.json"):
        self.client = AskAIClient()
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"[AIAnalyzer] Error loading config: {e}")
            self.config = {}

    def summarize_events(self, event_data: str) -> dict:
        """
        Generates personalized email content and returns as a dictionary with subject, body, and error.
        """
        model_str = self.config.get("model", "gpt-4")
        temperature = self.config.get("temperature", 0.5)
        max_tokens = self.config.get("max_tokens", 500)

        system_content = self.config.get("system_content")

        # Truncate event data to handle token limits
        truncated_data = self.truncate_event_data(event_data)

        user_content = (
            "Based on this Mixpanel data, write a personalized email following these EXACT formatting rules:\n"
            "1. Start with 'SUBJECT: ' followed by the subject line\n"
            "2. Then two newlines\n"
            "3. Then 'BODY:' followed by one newline\n"
            "4. Then the complete email body\n\n"
            f"Data to use:\n{truncated_data}"
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        try:
            response = self.client.ask_ai(
                messages=messages,
                model=AIModel(model_str),
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Parse response to extract subject and body
            response_text = response.strip()
            
            try:
                # Split response into sections
                subject = ""
                body = ""
                
                # First try to find subject
                if "SUBJECT:" in response_text:
                    subject_start = response_text.index("SUBJECT:") + 8
                    subject_end = response_text.find("\n\n", subject_start)
                    if subject_end != -1:
                        subject = response_text[subject_start:subject_end].strip()
                
                # Then try to find body
                if "BODY:" in response_text:
                    body_start = response_text.index("BODY:") + 5
                    body = response_text[body_start:].strip()
                
                # If parsing failed, use simple split as fallback
                if not subject or not body:
                    parts = response_text.split("\n\n")
                    for part in parts:
                        if part.startswith("SUBJECT:"):
                            subject = part.replace("SUBJECT:", "").strip()
                        elif part.startswith("BODY:"):
                            body = part.replace("BODY:", "").strip()
                
                print(f"[AIAnalyzer] Generated subject: {subject[:50]}...")
                print(f"[AIAnalyzer] Generated body length: {len(body)} chars")
                
                return {
                    "subject": subject,
                    "body": body,
                    "error": None
                }
            
            except Exception as parse_error:
                print(f"[AIAnalyzer] Error parsing response: {parse_error}")
                print(f"[AIAnalyzer] Raw response: {response_text[:200]}...")
                return {
                    "subject": "",
                    "body": "",
                    "error": f"Error parsing AI response: {str(parse_error)}"
                }

        except OpenAIError as e:
            error_msg = str(e)
            print(f"[AIAnalyzer] OpenAI error: {error_msg}")
            return {
                "subject": "",
                "body": "",
                "error": f"OpenAI error: {error_msg}"
            }

    def truncate_event_data(self, event_data: str) -> str:
        """
        Truncates event data to focus on the most recent and important events.
        """
        try:
            data = json.loads(event_data)
            
            # Keep essential profile properties
            profile = data.get("profile_properties", {})
            essential_props = {
                "firstname": profile.get("firstname", ""),
                "lastname": profile.get("lastname", ""),
                "email": profile.get("email", ""),
                "membership": profile.get("membership", ""),
                "subscription_status": profile.get("subscription_status", ""),
                "subscription_name": profile.get("subscription_name", ""),
                "subscription_cost": profile.get("subscription_cost", ""),
                "total_entries": profile.get("total_entries", 0),
                "job_count": profile.get("job_count", 0),
                "total_hours": profile.get("total_hours", 0),
                "user_subscribed": profile.get("user_subscribed", "")
            }
            
            # Keep important events
            events = data.get("user_events", [])
            important_events = [
                "Job Selected",
                "Create Job Save Button Clicked",
                "Job Dashboard Start Work At Clicked",
                "Subscription Selected",
                "Subscription Plan PURCHASED"
            ]
            
            filtered_events = []
            event_count = 0
            
            for event in events:
                if event_count >= 10:
                    break
                    
                event_name = event.get("event_name")
                if event_name in important_events:
                    filtered_events.append(event)
                    event_count += 1
            
            truncated_data = {
                "profile_properties": essential_props,
                "user_events": filtered_events
            }
            
            result = json.dumps(truncated_data, indent=2)
            print(f"[AIAnalyzer] Truncated data length: {len(result)} chars")
            return result
            
        except Exception as e:
            print(f"[AIAnalyzer] Error truncating event data: {e}")
            return event_data[:3000]