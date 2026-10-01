def provider_base_url(provider, configured=None):
    """Provider defaults are shared by connection probes and inference."""
    if configured and configured.strip():
        return configured.strip().rstrip("/")
    if provider == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta"
    if provider == "openai_compatible":
        return "https://api.openai.com/v1"
    raise ValueError("Unsupported cloud provider.")
