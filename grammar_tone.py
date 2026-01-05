"""
Grammar Check and Tone Adjustment for Decidim Translation Customizer

Handles LLM-based grammar checking and tone adjustment.
"""

import json
import re
import urllib.request
import urllib.error


class GrammarToneHandler:
    """Handles grammar checking and tone adjustment via LLM"""
    
    @staticmethod
    def extract_placeholders(text):
        """Extract all placeholders from text"""
        placeholders = []
        
        # Pattern for various placeholder formats
        patterns = [
            r'%\{[^}]+\}',  # %{name}
            r'\{\{[^}]+\}\}',  # {{count}}
            r'\{[^}]+\}',  # {count}
            r'%[sd]',  # %s, %d
            r'%[0-9]+\$[sd]',  # %1$s, %2$d
            r'%[0-9]+[sd]',  # %1s, %2d
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                placeholders.append(match.group())
        
        return sorted(set(placeholders))
    
    @staticmethod
    def validate_placeholders(original, corrected):
        """Validate that placeholders are preserved"""
        orig_placeholders = set(GrammarToneHandler.extract_placeholders(original))
        corr_placeholders = set(GrammarToneHandler.extract_placeholders(corrected))
        
        if orig_placeholders != corr_placeholders:
            return False, f"Placeholder mismatch. Original: {orig_placeholders}, Corrected: {corr_placeholders}"
        return True, None
    
    @staticmethod
    def call_llm_api(api_endpoint, api_key, model, messages, temperature):
        """Make a call to the LLM API"""
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        req = urllib.request.Request(
            api_endpoint,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'choices' not in result or not result['choices']:
                    raise Exception("Invalid API response: no choices")
                
                return result['choices'][0]['message']['content'].strip()
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_obj = error_json.get('error', {})
                
                # Try different error formats
                error_message = (
                    error_obj.get('message') or 
                    error_obj.get('description') or 
                    error_obj.get('error') or
                    error_body
                )
                error_type = error_obj.get('type', 'API Error')
                error_code = error_obj.get('code', str(e.code))
                
                if error_code == str(e.code) and 'code' in error_obj:
                    error_code = error_obj['code']
                
                detailed_error = f"API Error ({error_type}, Code: {error_code}): {error_message}"
            except:
                detailed_error = f"API Error (HTTP {e.code}): {error_body}"
            raise Exception(detailed_error)
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {str(e)}\n\nPlease check your internet connection and API endpoint URL.")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {str(e)}\n\nThe API may have returned an unexpected format.")
        except Exception as e:
            # Re-raise with more context if it's already our formatted error
            raise
    
    @staticmethod
    def parse_llm_response(response_text, expected_count):
        """Parse LLM response into list of corrected entries"""
        # Parse corrected entries (one per line)
        corrected_lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        # Remove numbering if present (e.g., "1. text" -> "text")
        corrected_entries = []
        for line in corrected_lines:
            # Remove leading number and dot/colon
            line = re.sub(r'^\d+[\.:]?\s*', '', line)
            corrected_entries.append(line)
        
        if len(corrected_entries) != expected_count:
            raise Exception(f"Expected {expected_count} corrections, got {len(corrected_entries)}")
        
        return corrected_entries
    
    @staticmethod
    def build_grammar_prompt(language, entries):
        """Build prompt for grammar checking"""
        system_prompt = f"""You are a grammar checker for {language} translations. Your task is to check and correct grammar errors while preserving ALL placeholders, HTML tags, Markdown syntax, URLs, and escape sequences exactly as they appear.

HARD CONSTRAINTS:
1. NEVER change placeholders: %{{name}}, %{{count}}, {{{{count}}}}, {{count}}, %s, %d, %1$s, etc.
2. NEVER change HTML tags, Markdown syntax, URLs, or escape sequences.
3. Keep the same meaning and tone (preserve formal vs informal, product terminology).
4. Prefer UI-friendly concise text.
5. If the text is already correct, return it unchanged.

{"GERMAN-SPECIFIC CHECKS (if language is de or de-CH):" if language.lower() in ['de', 'de-ch'] else ""}
- Check clause order and verb-final position in subordinate clauses.
- Check comma rules (including "dass", relative clauses, infinitive clauses).
- Check agreement (case, number, gender).
- Ensure consistent "Sie" forms and capitalization.
- Avoid overly long nested sentences; split only when clearly better.

For each entry, return ONLY the corrected text (or original if no changes needed). No explanations, no commentary."""

        user_prompt = "Check and correct the following translation entries. Return each corrected entry on a new line, in the same order:\n\n"
        for i, (key, value) in enumerate(entries, 1):
            user_prompt += f"{i}. {value}\n"
        
        return system_prompt, user_prompt
    
    @staticmethod
    def build_tone_prompt(language, tone_mode, entries):
        """Build prompt for tone adjustment"""
        if tone_mode == "formal":
            tone_instruction = "Convert all text to formal German using 'Sie' form. Use formal verb forms, formal pronouns (Sie, Ihnen, Ihr), and formal capitalization."
        elif tone_mode == "informal":
            tone_instruction = "Convert all text to informal German using 'Du' form. Use informal verb forms, informal pronouns (du, dir, dein), and informal capitalization."
        else:
            raise Exception(f"Invalid tone mode: {tone_mode}")
        
        system_prompt = f"""You are a tone adjuster for {language} translations. Your task is to adjust the tone of the text while preserving ALL placeholders, HTML tags, Markdown syntax, URLs, and escape sequences exactly as they appear.

HARD CONSTRAINTS:
1. NEVER change placeholders: %{{name}}, %{{count}}, {{{{count}}}}, {{count}}, %s, %d, %1$s, etc.
2. NEVER change HTML tags, Markdown syntax, URLs, or escape sequences.
3. Keep the same meaning and product terminology.
4. Prefer UI-friendly concise text.
5. If the text already has the desired tone, return it unchanged.

TONE ADJUSTMENT:
{tone_instruction}

For each entry, return ONLY the adjusted text (or original if no changes needed). No explanations, no commentary."""

        user_prompt = f"Adjust the tone of the following {language} translation entries to {tone_mode}. Return each adjusted entry on a new line, in the same order:\n\n"
        for i, (key, value) in enumerate(entries, 1):
            user_prompt += f"{i}. {value}\n"
        
        return system_prompt, user_prompt

