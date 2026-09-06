MODULE_TYPE = "auxiliary"  # Changed from "chatgpt" - must be valid type
from collections import OrderedDict
import sys
import os
import time

class ModuleClass:
    def __init__(self):
        self.info = {
            'Name': 'AI Chat Interface',
            'Rank': 'Good',
            'Platform': 'Windows/Linux/MacOS',
            'Architectures': 'x86/x64 (requires GPU for best performance)',
            'Description': 'AI-powered chat interface with local model support',
            'Version': '1.0',
            'Author': 'KentScript',
            'Options': OrderedDict([
                ('MODEL', ('local', True, 'Model type: local/openai/huggingface')),
                ('PROMPT', ('Hello, how are you?', True, 'Input prompt for AI')),
                ('MAX_LENGTH', ('100', False, 'Maximum response length')),
                ('TEMPERATURE', ('0.7', False, 'Creativity level (0.1-1.0)')),
                ('MODE', ('normal', False, 'Response mode: normal/creative/detailed')),
                ('SAVE_LOG', ('false', False, 'Save conversation to log (true/false)')),
                ('LOG_FILE', ('chat_log.txt', False, 'Log file path')),
            ])
        }
        self.conversation_history = []
    
    def help(self):
        return """
AI Chat Interface
=================
Interactive AI chat using various models.

Required:
  set PROMPT <your_message>

Optional:
  set MODEL <local/openai/huggingface>
  set MAX_LENGTH <number>
  set TEMPERATURE <0.1-1.0>
  set MODE <normal/creative/detailed>
  set SAVE_LOG true
  set LOG_FILE <path>

Examples:
  # Basic chat
  set PROMPT "Explain quantum computing"
  run
  
  # Creative response
  set PROMPT "Write a short story about a hacker"
  set TEMPERATURE 0.9
  set MAX_LENGTH 200
  set MODE creative
  run
  
  # Save conversation
  set PROMPT "What is cybersecurity?"
  set SAVE_LOG true
  set LOG_FILE /tmp/chat_history.txt
  run

Note: Local model requires transformers library: pip install transformers torch
"""
    
    def _check_dependencies(self, model_type):
        """Check if required libraries are installed"""
        if model_type == 'local':
            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForCausalLM
                return True, ""
            except ImportError:
                return False, "[-] Local model requires: pip install transformers torch"
        
        elif model_type == 'openai':
            try:
                import openai
                return True, ""
            except ImportError:
                return False, "[-] OpenAI requires: pip install openai"
        
        elif model_type == 'huggingface':
            try:
                from transformers import pipeline
                return True, ""
            except ImportError:
                return False, "[-] HuggingFace requires: pip install transformers"
        
        return True, ""
    
    def _get_local_response(self, prompt, max_length, temperature, mode):
        """Get response using local model"""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            # Use smaller model for faster response
            model_name = "microsoft/DialoGPT-small"
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Tokenize input
            inputs = tokenizer.encode(prompt + tokenizer.eos_token, return_tensors='pt')
            
            # Generate response
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_length=int(max_length),
                    temperature=float(temperature),
                    top_k=50,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            # Decode response
            response = tokenizer.decode(outputs[:, inputs.shape[-1]:][0], skip_special_tokens=True)
            
            # Apply mode adjustments
            if mode == 'creative':
                response = self._enhance_creativity(response)
            elif mode == 'detailed':
                response = self._add_detail(response)
            
            return response
            
        except Exception as e:
            return f"[ERROR] Local model failed: {str(e)}"
    
    def _get_mock_response(self, prompt, max_length, temperature, mode):
        """Mock AI response when no model is available"""
        responses = [
            f"I understand you're asking about '{prompt}'. This is a simulated response since AI models are not installed.",
            f"Based on your query '{prompt[:50]}...', I would analyze the topic and provide insights.",
            f"To properly answer '{prompt}', you would need to install AI libraries.",
            f"This is a demonstration response. Install transformers for real AI chat.",
            f"Query received: '{prompt}'. Enable local models for actual AI responses."
        ]
        
        import random
        response = random.choice(responses)
        
        # Adjust based on temperature
        if float(temperature) > 0.8:
            response = response + " " + " ".join(["Creative addition."] * random.randint(1, 3))
        
        # Limit length
        if len(response) > int(max_length):
            response = response[:int(max_length)] + "..."
        
        return response
    
    def _enhance_creativity(self, text):
        """Enhance text creativity"""
        import random
        enhancements = [
            "Imagine this: ",
            "From a creative perspective: ",
            "Let me paint you a picture: ",
            "In an imaginative scenario: ",
        ]
        return random.choice(enhancements) + text
    
    def _add_detail(self, text):
        """Add more detail to response"""
        details = [
            " Let me elaborate on this point.",
            " To provide more context,",
            " Additionally, it's important to note that",
            " From a detailed perspective,"
        ]
        import random
        return text + random.choice(details)
    
    def _clean_response(self, response):
        """Clean and format the response"""
        # Remove any markdown formatting
        import re
        response = re.sub(r'\*+', '', response)
        response = re.sub(r'`', '', response)
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Ensure proper sentence structure
        response = response.strip()
        if response and not response.endswith(('.', '!', '?')):
            response = response + '.'
        
        return response
    
    def _log_conversation(self, prompt, response, log_file):
        """Save conversation to log file"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Prompt: {prompt}\n")
                f.write(f"Response: {response}\n")
            return True
        except Exception as e:
            return False
    
    def execute(self):
        """Main execution method"""
        try:
            # Get options
            model_type = self.info['Options']['MODEL'][0].lower()
            prompt = self.info['Options']['PROMPT'][0]
            max_length = int(self.info['Options']['MAX_LENGTH'][0])
            temperature = float(self.info['Options']['TEMPERATURE'][0])
            mode = self.info['Options']['MODE'][0].lower()
            save_log = self.info['Options']['SAVE_LOG'][0].lower() == 'true'
            log_file = self.info['Options']['LOG_FILE'][0]
            
            # Validate temperature
            if temperature < 0.1 or temperature > 1.0:
                return "[-] Temperature must be between 0.1 and 1.0"
            
            # Validate max length
            if max_length < 10 or max_length > 1000:
                return "[-] Max length must be between 10 and 1000"
            
            # Check dependencies
            dep_check, dep_error = self._check_dependencies(model_type)
            if not dep_check:
                print(dep_error)
                print("[*] Using mock responses instead")
                model_type = 'mock'
            
            # Display info
            results = []
            results.append(f"[+] AI Chat Interface")
            results.append(f"[+] Model: {model_type}")
            results.append(f"[+] Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            results.append(f"[+] Settings: Length={max_length}, Temp={temperature}, Mode={mode}")
            
            if save_log:
                results.append(f"[+] Logging to: {log_file}")
            
            results.append("\n" + "="*60)
            
            print("\n".join(results))
            
            # Get response based on model type
            if model_type == 'local':
                response = self._get_local_response(prompt, max_length, temperature, mode)
            elif model_type == 'openai':
                response = "[INFO] OpenAI integration requires API key setup"
            elif model_type == 'huggingface':
                response = "[INFO] HuggingFace integration requires model selection"
            else:
                response = self._get_mock_response(prompt, max_length, temperature, mode)
            
            # Clean response
            response = self._clean_response(response)
            
            # Display response
            print(f"\n[AI Response]:")
            print(f"{response}\n")
            
            # Save to log if requested
            if save_log:
                if self._log_conversation(prompt, response, log_file):
                    print(f"[+] Conversation saved to: {log_file}")
                else:
                    print("[-] Failed to save log")
            
            # Add to history
            self.conversation_history.append({
                'timestamp': time.time(),
                'prompt': prompt,
                'response': response[:100] + "..." if len(response) > 100 else response
            })
            
            # Return summary
            return f"[+] Chat completed. Response length: {len(response)} characters."
            
        except KeyboardInterrupt:
            return "\n[!] Chat interrupted by user"
        except Exception as e:
            return f"[-] Chat failed: {str(e)}"

# Test when run directly
if __name__ == "__main__":
    module = ModuleClass()
    print(module.execute())