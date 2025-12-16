# HuggingFace Model Setup Guide

## Quick Start

### 1. Get Your HuggingFace Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Choose "Read" permission (you only need read access)
4. Copy the token

### 2. Set Environment Variable

```bash
# Add to your .env file
echo "HF_TOKEN=hf_your_token_here" >> backend/.env

# Or export directly
export HF_TOKEN="hf_your_token_here"
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This includes:
- `tiktoken>=0.7.0` - Accurate token counting
- `openai>=1.0.0` - HuggingFace API compatibility
- `huggingface-hub>=0.20.0` - Already included

## Model Selection Guide

### For Speed (Recommend: **Mistral 7B**)
- **Model ID**: `mistral`
- **Speed**: 100-200 tokens/sec
- **Cost**: ~$0.00014 per 1K tokens
- **Use Case**: General documentation, real-time responses
- **Setup**: `HF_TOKEN=hf_... python backend/main.py`
- **Usage**: `{"model": "mistral"}`

### For Quality (Recommend: **Mixtral 8x7B**)
- **Model ID**: `mixtral`
- **Speed**: 80-150 tokens/sec
- **Cost**: ~$0.00024 per 1K tokens
- **Use Case**: Complex reasoning, detailed explanations
- **Setup**: Same as above
- **Usage**: `{"model": "mixtral"}`

### For Multilingual (Recommend: **Qwen 2.5 72B**)
- **Model ID**: `qwen`
- **Speed**: 50-100 tokens/sec
- **Cost**: ~$0.00032 per 1K tokens
- **Best For**: Multi-language support, detailed documentation
- **Setup**: Same as above
- **Usage**: `{"model": "qwen"}`

### For Open Source (Recommend: **Llama 3.1 70B**)
- **Model ID**: `llama`
- **Speed**: 60-120 tokens/sec
- **Cost**: ~$0.00027 per 1K tokens
- **Best For**: Open-source preference, good general performance
- **Setup**: Same as above
- **Usage**: `{"model": "llama"}`

### For Budget/Speed (Recommend: **Kimi K2**)
- **Model ID**: `k2`
- **Speed**: 40-80 tokens/sec
- **Cost**: ~$0.00015 per 1K tokens
- **Best For**: Cost-critical applications, Chinese content
- **Setup**: Same as above
- **Usage**: `{"model": "k2"}`

## Model Aliases

You can use these shortcuts:

```python
from services.llm_service import get_llm_service

# These all work:
mistral_model = get_llm_service("mistral")
mixtral_model = get_llm_service("mixtral")
qwen_model = get_llm_service("qwen")
llama_model = get_llm_service("llama")
k2_model = get_llm_service("k2")

# Or with hf- prefix
mistral2 = get_llm_service("hf-mistral")
mixtral2 = get_llm_service("hf-mixtral")
```

## API Integration

### Frontend: Select Model When Generating Journey

```typescript
// frontend/app/page.tsx
const handleGenerateJourney = async (query: string) => {
  const response = await fetch(`${API_BASE_URL}/journey/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      max_steps: 10,
      project: selectedProject,
      model: selectedModel  // "mistral", "qwen", "mixtral", etc.
    }),
  });
  // ...
};
```

### Backend: Use Selected Model

```python
# backend/api/journey.py
@router.post("/generate")
async def generate_journey(request: JourneyRequest):
    generator = JourneyGenerator(model_name=request.model)
    response = generator.generate_journey(request.query, request.max_steps)
    return response
```

## Performance Comparison

### Cost per 1M Tokens

| Model | Input | Output | Journey (est.) |
|-------|-------|--------|----------------|
| Claude Sonnet | $3 | $15 | $2.50-5.00 |
| **Mistral 7B** | **$0.14** | **$0.42** | **$0.08-0.20** |
| **Mixtral 8x7B** | **$0.24** | **$0.72** | **$0.15-0.35** |
| **Qwen 2.5 72B** | **$0.32** | **$0.96** | **$0.20-0.45** |
| **Llama 3.1 70B** | **$0.27** | **$0.81** | **$0.17-0.40** |
| **Kimi K2** | **$0.15** | **$0.45** | **$0.10-0.25** |

**Savings Example:**
- 1000 journeys/month with Claude: ~$2,500-5,000
- 1000 journeys/month with Mistral: ~$80-200
- **Savings: 96%** ✅

### Quality Comparison

| Model | General | Code | Math | Reasoning |
|-------|---------|------|------|-----------|
| Claude | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Mistral | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Mixtral** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Qwen** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Llama** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Kimi K2** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Testing Your Setup

### Test 1: Basic Model Access

```bash
cd backend
python3 << 'EOF'
from services.llm_service import get_llm_service

# Test HuggingFace model
mistral = get_llm_service("mistral")
response = mistral.generate("Hello, what is Python?", max_tokens=100)
print(f"✅ Model working! Response: {response[:100]}...")
EOF
```

### Test 2: Semantic Truncation

```bash
python3 << 'EOF'
from services.semantic_truncation import SemanticTruncator

truncator = SemanticTruncator("mistral")

long_text = """
# Python Basics

Python is a high-level programming language. It's easy to learn and read.

## Getting Started

To start with Python, you need to install it. You can download from python.org.

## Variables

Variables store data values. In Python, you don't need to declare types explicitly.
"""

truncated = truncator.truncate_intelligently(long_text, max_tokens=50)
print("✅ Truncation working!")
print(truncated)
EOF
```

### Test 3: Full Journey Generation

```bash
# Start the backend
cd backend
uvicorn main:app --reload

# In another terminal, test the API
curl -X POST http://localhost:8000/api/journey/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I set up authentication?",
    "max_steps": 5,
    "model": "mistral",
    "project": "privy"
  }'
```

## Troubleshooting

### Error: "HF_TOKEN not set"
```bash
# Check if token is set
echo $HF_TOKEN

# If empty, set it
export HF_TOKEN="hf_your_token_here"

# Verify
echo $HF_TOKEN  # Should show your token
```

### Error: "Model not found"
```
Error: 404 Client Error: Not Found for url: https://router.huggingface.co/v1/models/...
```

**Cause**: Model ID is incorrect or model is removed from HF

**Solution**: Check the model exists on https://huggingface.co/models
- Mistral 7B: https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2
- Mixtral 8x7B: https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1

### Error: "Rate limited"
```
Error: 429 Too Many Requests
```

**Cause**: Model is overloaded

**Solution**: 
- Try a different model
- Use the `:vllm` suffix for optimized routing
- Wait a minute and retry

### Error: "Insufficient tokens"
```
Error: 402 Payment Required
```

**Cause**: HuggingFace free trial quota exceeded or account needs credit

**Solution**:
- Add payment method to HF account
- Or use Claude (ANTHROPIC_API_KEY)

## Recommended Setup

For best results with docsBuddy, we recommend:

### Development
```bash
export HF_TOKEN="hf_your_token_here"
export LLM_MODEL="mistral"  # Fast, cheap
```

### Production
```bash
# Use Mixtral for better quality
export LLM_MODEL="mixtral"
# Or use Qwen for multilingual support
export LLM_MODEL="qwen"
```

### Cost-Optimized
```bash
# Use Kimi K2 - very cheap with good quality
export LLM_MODEL="k2"
```

## Next Steps

1. ✅ Get HF token
2. ✅ Add to .env file
3. ✅ Run test script above
4. ✅ Try with frontend at http://localhost:3000
5. ✅ Monitor costs on HuggingFace dashboard

## Resources

- [HuggingFace Docs](https://huggingface.co/docs)
- [HuggingFace Inference API](https://huggingface.co/inference-api)
- [Model Leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard)
- [Token Pricing](https://huggingface.co/pricing)
