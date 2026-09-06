#!/usr/bin/env python3
"""
Responses API → Chat Completions API translation proxy.

Converts OpenAI Responses API format (used by infosec/codex) to
Chat Completions format (used by Mistral, Groq, Gemini, etc.).

Usage:
    python3 responses_proxy.py [--port 8080] [--provider mistral|groq|gemini]

Environment:
    MISTRAL_API_KEY - API key for Mistral
    GROQ_API_KEY    - API key for Groq
    GEMINI_API_KEY  - API key for Gemini
"""

import argparse
import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

PROVIDERS = {
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1/chat/completions",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-small-latest",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "env_key": "GROQ_API_KEY",
        "default_model": "qwen/qwen3.6-27b",
    },
    "gemini": {
        "name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
}

# Provider keys from user
PROVIDER_KEYS = {
    "mistral": os.environ.get("MISTRAL_API_KEY", ""),
    "groq": os.environ.get("GROQ_API_KEY", ""),
    "gemini": os.environ.get("GEMINI_API_KEY", ""),
}


def responses_tools_to_chat_tools(tools):
    """Convert Responses API tool format to Chat Completions format."""
    if not tools:
        return None
    chat_tools = []
    for tool in tools:
        if tool.get("type") == "function":
            chat_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            })
        elif tool.get("type") in ("web_search_preview", "web_search"):
            chat_tools.append({"type": "web_search"})
        elif tool.get("type") == "code_interpreter":
            chat_tools.append({"type": "code_interpreter"})
        else:
            chat_tools.append(tool)
    return chat_tools if chat_tools else None


def responses_input_to_chat_messages(input_items, instructions=""):
    """Convert Responses API input items to Chat Completions messages."""
    messages = []

    if instructions:
        messages.append({"role": "system", "content": instructions})

    for item in input_items:
        item_type = item.get("type", "")

        if item_type == "message":
            role = item.get("role", "user")
            # Mistral/Groq don't support "developer" role — convert to "system"
            if role == "developer":
                role = "system"
            content_parts = item.get("content", [])
            if isinstance(content_parts, str):
                messages.append({"role": role, "content": content_parts})
            elif isinstance(content_parts, list):
                text_parts = []
                for part in content_parts:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif part.get("type") == "input_text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "output_text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        messages.append({
                            "role": role,
                            "content": [{"type": "image_url", "image_url": part.get("image_url", {})}],
                        })
                        continue
                if text_parts:
                    messages.append({"role": role, "content": "\n".join(text_parts)})

        elif item_type == "function_call":
            messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": item.get("call_id", item.get("id", str(uuid.uuid4()))),
                    "type": "function",
                    "function": {
                        "name": item.get("name", ""),
                        "arguments": item.get("arguments", "{}"),
                    },
                }],
            })

        elif item_type == "function_call_output":
            messages.append({
                "role": "tool",
                "tool_call_id": item.get("call_id", item.get("id", "")),
                "content": str(item.get("output", "")),
            })

        elif item_type == "reasoning":
            pass  # Skip reasoning items, they're internal

    return messages


def chat_chunk_to_responses_events(chunk, response_id):
    """Convert a Chat Completions chunk to Responses API events."""
    events = []
    choices = chunk.get("choices", [])
    if not choices:
        return events

    for choice in choices:
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        # Text content delta
        content = delta.get("content")
        if content:
            events.append({
                "type": "response.output_text.delta",
                "item_id": f"item_{response_id}",
                "delta": content,
                "content_index": 0,
            })

        # Tool calls
        tool_calls = delta.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            if func.get("name"):
                # Tool call start
                events.append({
                    "type": "response.output_item.added",
                    "item_id": f"item_{response_id}_tc_{tc.get('index', 0)}",
                    "item": {
                        "type": "function_call",
                        "id": f"fc_{response_id}_{tc.get('index', 0)}",
                        "call_id": f"call_{response_id}_{tc.get('index', 0)}",
                        "name": func["name"],
                        "arguments": "",
                        "status": "in_progress",
                    },
                    "output_index": len([e for e in events if e["type"] == "response.output_item.added"]),
                })
            if func.get("arguments"):
                events.append({
                    "type": "response.custom_tool_call_input.delta",
                    "item_id": f"item_{response_id}_tc_{tc.get('index', 0)}",
                    "call_id": f"call_{response_id}_{tc.get('index', 0)}",
                    "delta": func["arguments"],
                })

        # Finish
        if finish_reason:
            if finish_reason == "stop":
                events.append({
                    "type": "response.completed",
                    "response": {
                        "id": response_id,
                        "status": "completed",
                        "end_turn": True,
                        "usage": chunk.get("usage", {}),
                    },
                })
            elif finish_reason == "tool_calls":
                events.append({
                    "type": "response.completed",
                    "response": {
                        "id": response_id,
                        "status": "completed",
                        "end_turn": False,
                        "usage": chunk.get("usage", {}),
                    },
                })

    return events


class ResponsesProxyHandler(BaseHTTPRequestHandler):
    provider_name = "mistral"

    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            req = json.loads(body)
        except json.JSONDecodeError as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return

        # Only handle /responses endpoint
        if "/responses" not in self.path and self.path != "/":
            self.send_error(404, f"Unknown path: {self.path}")
            return

        provider = PROVIDERS[self.provider_name]
        api_key = PROVIDER_KEYS[self.provider_name]

        # Convert request
        chat_messages = responses_input_to_chat_messages(
            req.get("input", []),
            req.get("instructions", ""),
        )
        chat_tools = responses_tools_to_chat_tools(req.get("tools"))
        model = req.get("model", provider["default_model"])
        stream = req.get("stream", True)

        chat_request = {
            "model": model,
            "messages": chat_messages,
            "stream": stream,
            "max_tokens": 4096,
        }
        if chat_tools:
            chat_request["tools"] = chat_tools
            tool_choice = req.get("tool_choice", "auto")
            if tool_choice and tool_choice != "auto":
                chat_request["tool_choice"] = {"type": "auto"}

        response_id = f"resp_{uuid.uuid4().hex[:24]}"

        # Forward to provider
        try:
            req_data = json.dumps(chat_request).encode()
            http_req = urllib.request.Request(
                provider["base_url"],
                data=req_data,
                method="POST",
            )
            http_req.add_header("Content-Type", "application/json")
            http_req.add_header("Authorization", f"Bearer {api_key}")

            ctx = ssl.create_default_context()
            http_resp = urllib.request.urlopen(http_req, timeout=120, context=ctx)

            if stream:
                self._handle_streaming_response(http_resp, response_id, req)
            else:
                self._handle_non_streaming_response(http_resp, response_id)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:2000]
            print(f"[PROXY] Provider error {e.code}: {err_body}", file=sys.stderr)
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "type": "response.failed",
                "response": {
                    "id": response_id,
                    "status": "failed",
                    "error": {"message": err_body, "code": str(e.code)},
                },
            }).encode())
        except Exception as e:
            print(f"[PROXY] Error: {e}", file=sys.stderr)
            self.send_error(502, str(e))

    def _handle_streaming_response(self, http_resp, response_id, original_req):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("x-request-id", f"req_{uuid.uuid4().hex[:16]}")
        self.end_headers()

        # Send response.created
        created_event = {
            "type": "response.created",
            "response": {
                "id": response_id,
                "status": "in_progress",
                "output": [],
                "model": original_req.get("model", ""),
            },
        }
        self._write_sse("response.created", created_event)

        # Send response.in_progress
        self._write_sse("response.in_progress", {
            "type": "response.in_progress",
            "response": {"id": response_id, "status": "in_progress"},
        })

        # Track tool calls for assembly
        tool_calls_accum = {}
        output_items = []
        full_text = ""
        text_item_added = False

        # Read streaming response from provider
        buffer = ""
        for chunk in http_resp:
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        # Send completed
                        completed_event = {
                            "type": "response.completed",
                            "response": {
                                "id": response_id,
                                "status": "completed",
                                "end_turn": True,
                            },
                        }
                        self._write_sse("response.completed", completed_event)
                        return

                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk_data.get("choices", [])
                    for choice in choices:
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")

                        # Text content
                        content = delta.get("content")
                        if content:
                            if not text_item_added:
                                self._write_sse("response.output_item.added", {
                                    "type": "response.output_item.added",
                                    "item_id": f"item_{response_id}",
                                    "item": {
                                        "type": "message",
                                        "id": f"msg_{response_id}",
                                        "role": "assistant",
                                        "content": [],
                                        "status": "in_progress",
                                    },
                                    "output_index": 0,
                                })
                                text_item_added = True
                            full_text += content
                            self._write_sse("response.output_text.delta", {
                                "type": "response.output_text.delta",
                                "item_id": f"item_{response_id}",
                                "delta": content,
                                "content_index": 0,
                            })

                        # Tool calls
                        for tc in delta.get("tool_calls", []):
                            idx = tc.get("index", 0)
                            func = tc.get("function", {})
                            if idx not in tool_calls_accum:
                                tool_calls_accum[idx] = {
                                    "id": f"fc_{response_id}_{idx}",
                                    "call_id": f"call_{response_id}_{idx}",
                                    "name": func.get("name", ""),
                                    "arguments": "",
                                }
                            if func.get("name"):
                                tool_calls_accum[idx]["name"] = func["name"]
                            if func.get("arguments"):
                                tool_calls_accum[idx]["arguments"] += func["arguments"]

                            # Emit delta
                            self._write_sse("response.custom_tool_call_input.delta", {
                                "type": "response.custom_tool_call_input.delta",
                                "item_id": f"item_{response_id}_tc_{idx}",
                                "call_id": tool_calls_accum[idx]["call_id"],
                                "delta": func.get("arguments", ""),
                            })

                        # Finish
                        if finish_reason:
                            # Emit completed tool call items
                            for idx, tc in tool_calls_accum.items():
                                self._write_sse("response.output_item.done", {
                                    "type": "response.output_item.done",
                                    "item_id": f"item_{response_id}_tc_{idx}",
                                    "item": {
                                        "type": "function_call",
                                        "id": tc["id"],
                                        "call_id": tc["call_id"],
                                        "name": tc["name"],
                                        "arguments": tc["arguments"],
                                        "status": "completed",
                                    },
                                })

                            # If there's text, emit the text item done
                            if full_text and not tool_calls_accum:
                                self._write_sse("response.output_item.done", {
                                    "type": "response.output_item.done",
                                    "item_id": f"item_{response_id}",
                                    "item": {
                                        "type": "message",
                                        "id": f"msg_{response_id}",
                                        "role": "assistant",
                                        "content": [{"type": "output_text", "text": full_text}],
                                        "status": "completed",
                                    },
                                })

                            completed_event = {
                                "type": "response.completed",
                                "response": {
                                    "id": response_id,
                                    "status": "completed",
                                    "end_turn": finish_reason == "stop",
                                },
                            }
                            self._write_sse("response.completed", completed_event)
                            return

        # If we get here without [DONE], send completed anyway
        self._write_sse("response.completed", {
            "type": "response.completed",
            "response": {"id": response_id, "status": "completed", "end_turn": True},
        })

    def _handle_non_streaming_response(self, http_resp, response_id):
        data = json.loads(http_resp.read())
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response = {
            "id": response_id,
            "status": "completed",
            "output": [{
                "type": "message",
                "id": f"msg_{response_id}",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
                "status": "completed",
            }],
            "usage": data.get("usage", {}),
        }
        self.wfile.write(json.dumps(response).encode())

    def _write_sse(self, event_type, data):
        try:
            payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(payload.encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description="Responses API → Chat Completions proxy")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--provider", choices=PROVIDERS.keys(), default="mistral",
                        help="Provider to use")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    ResponsesProxyHandler.provider_name = args.provider

    provider = PROVIDERS[args.provider]
    api_key = PROVIDER_KEYS[args.provider]
    if not api_key:
        print(f"Error: Set {provider['env_key']} environment variable", file=sys.stderr)
        sys.exit(1)

    server = HTTPServer((args.host, args.port), ResponsesProxyHandler)
    print(f"[PROXY] Listening on {args.host}:{args.port}")
    print(f"[PROXY] Provider: {provider['name']} ({provider['base_url']})")
    print(f"[PROXY] Model: {provider['default_model']}")
    print(f"[PROXY] Point infosec at: http://{args.host}:{args.port}/v1")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[PROXY] Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
