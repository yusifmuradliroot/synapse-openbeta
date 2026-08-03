import json
import urllib.request
import urllib.error

MODE_PARAMS = {
    "chat": {"temperature": 0.5, "top_p": 0.9, "max_tokens": 2048, "reasoning_budget": 1024},
    "code": {"temperature": 0.1, "top_p": 0.95, "max_tokens": 4096, "reasoning_budget": 2048},
    "agent": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 8192, "reasoning_budget": 4096},
}

class Engine:
    def __init__(self):
        self.api_key = self.model = self.api_url = self.provider_name = ""
        self.provider_type = "openai"
        self.headers = {}
        self.ctx_in = self.ctx_out = self.sess_in = self.sess_out = 0
        self.tokens_exact = False
        self.temperature = 0.5
        self.top_p = 0.9
        self.max_tokens = 2048
        self.reasoning_budget = 1024

    def apply(self, name, providers):
        if name not in providers:
            return False
        p = providers[name]
        if not p.get("api_key") or "YOUR_" in p.get("api_key", ""):
            return False
        self.provider_name = name
        self.api_key = p["api_key"]
        self.model = p["model"]
        self.api_url = p["api_url"]
        self.provider_type = "cohere" if "cohere" in self.api_url.lower() else "openai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Synapse/3.0"
        }
        return True

    def set_mode_params(self, mode):
        params = MODE_PARAMS.get(mode, MODE_PARAMS["chat"])
        self.temperature = params["temperature"]
        self.top_p = params["top_p"]
        self.max_tokens = params["max_tokens"]
        self.reasoning_budget = params["reasoning_budget"]

    def est_tok(self, t):
        return max(0, len(t.encode("utf-8")) // 4)

    def stream(self, messages):
        if self.provider_type == "cohere":
            yield from self._stream_cohere(messages)
        else:
            yield from self._stream_openai(messages)

    def _stream_openai(self, messages):
        self.ctx_in = self.est_tok(json.dumps(messages))
        self.ctx_out = 0
        self.tokens_exact = False
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens
        }
        if "nvidia" in self.api_url.lower():
            payload["chat_template_kwargs"] = {"enable_thinking": True}
            payload["reasoning_budget"] = self.reasoning_budget
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    if line[6:] == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line[6:])
                        if chunk.get("usage"):
                            self.ctx_in = chunk["usage"].get("prompt_tokens", self.ctx_in)
                            self.ctx_out = chunk["usage"].get("completion_tokens", self.ctx_out)
                            self.tokens_exact = True
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        c = delta.get("content", "")
                        r = delta.get("reasoning", "") or delta.get("reasoning_content", "")
                        if c:
                            yield "content", c
                        if r:
                            yield "reasoning", r
                    except Exception:
                        continue
        except urllib.error.HTTPError as e:
            yield "error", f"[HTTP {e.code}] {e.read().decode('utf-8', errors='ignore')[:200]}"
        except Exception as e:
            yield "error", f"[Error] {str(e)}"

    def _stream_cohere(self, messages):
        self.ctx_in = self.est_tok(json.dumps(messages))
        self.ctx_out = 0
        self.tokens_exact = False
        preamble_parts = []
        non_system = []
        for m in messages:
            if m.get("role") == "system":
                preamble_parts.append(m.get("content", ""))
            else:
                non_system.append(m)
        if not non_system:
            yield "error", "No message to send"
            return
        last_msg = non_system[-1]
        chat_history = []
        for m in non_system[:-1]:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "user":
                chat_history.append({"role": "USER", "message": content})
            elif role == "assistant":
                chat_history.append({"role": "CHATBOT", "message": content})
        payload = {
            "model": self.model,
            "message": last_msg.get("content", ""),
            "stream": True,
            "preamble": "\n".join(preamble_parts),
            "chat_history": chat_history,
            "temperature": self.temperature
        }
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        ev = chunk.get("event_type", "")
                        if ev == "text-generation":
                            t = chunk.get("text", "")
                            if t:
                                self.ctx_out += self.est_tok(t)
                                yield "content", t
                        elif ev == "stream-end":
                            meta = chunk.get("response", {}).get("meta", {})
                            tokens = meta.get("tokens", {})
                            if tokens:
                                self.ctx_in = tokens.get("input_tokens", self.ctx_in)
                                self.ctx_out = tokens.get("output_tokens", self.ctx_out)
                                self.tokens_exact = True
                    except Exception:
                        continue
        except urllib.error.HTTPError as e:
            yield "error", f"[HTTP {e.code}] {e.read().decode('utf-8', errors='ignore')[:200]}"
        except Exception as e:
            yield "error", f"[Error] {str(e)}"
