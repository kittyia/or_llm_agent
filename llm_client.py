# llm_client.py
# NOTE: This file was created earlier but to keep changes minimal for the project
# we replace it with a harmless stub so it doesn't introduce additional behavior.
# The project's scripts read OPENAI_API_KEY and OPENAI_API_BASE from the environment
# (and accept command-line overrides like --OPENAI_API_KEY=... and --OPENAI_API_BASE=...).

"""Stub module retained for compatibility if referenced elsewhere."""

def init_clients(*args, **kwargs):
    # noop: initialization is handled by scripts via environment variables
    return None

def get_openai_client(async_mode=False):
    raise RuntimeError("get_openai_client is not implemented in the stub. Scripts use environment-based clients.")

def get_anthropic_client(async_mode=False):
    raise RuntimeError("get_anthropic_client is not implemented in the stub. Scripts use environment-based clients.")


def get_openai_params(openai_api_key=None, openai_api_base=None):
    import os
    ak = openai_api_key if openai_api_key is not None else os.getenv("OPENAI_API_KEY")
    base = openai_api_base if openai_api_base is not None else os.getenv("OPENAI_API_BASE")
    return dict(api_key=ak, base_url=base)

