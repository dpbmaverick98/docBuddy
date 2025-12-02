# RAG Improvements with LlamaIndex

## What We Added

### 1. LlamaIndex Integration
- Wraps ChromaDB with LlamaIndex for better RAG capabilities
- Uses existing embeddings (no re-indexing needed)
- Provides context optimization and post-processing

### 2. Intent Extraction
- Extracts structured intent from user queries
- Identifies: goal, complexity, platform, keywords, requirements
- Used to enhance search and prompt generation

### 3. Prompt Chaining
- Multi-step prompt workflows
- Context passing between steps
- Context window optimization

### 4. Temperature & Sampling Controls
- Configurable temperature per service
- Journey generation: 0.7 (balanced)
- Summaries: 0.3 (more focused)
- Q&A: 0.7 (more conversational)

## Architecture

```
User Query
    ↓
Intent Extraction (temperature: 0.3)
    ↓
RAG Search with Intent (LlamaIndex + ChromaDB)
    ↓
Context Optimization (select top docs, fit in window)
    ↓
Journey Generation (temperature: 0.7)
    ↓
Validation & Response
```

## Usage

### Basic (with RAG)
```python
generator = JourneyGenerator(use_rag=True, temperature=0.7)
journey = generator.generate_journey("set up authentication")
```

### Custom Temperature
```python
generator = JourneyGenerator(temperature=0.5)  # More deterministic
journey = generator.generate_journey("set up auth", temperature=0.9)  # Override
```

### Without RAG (legacy)
```python
generator = JourneyGenerator(use_rag=False)
journey = generator.generate_journey("set up authentication")
```

## API Changes

New optional parameters:
```json
{
  "query": "set up authentication",
  "max_steps": 5,
  "temperature": 0.7,  // Optional: 0.0-1.0
  "use_rag": true      // Optional: Use LlamaIndex (default: true)
}
```

## Benefits

1. **Better Search**: Intent-aware retrieval
2. **Optimized Context**: Fits relevant docs in token limit
3. **Flexible Temperature**: Adjust creativity per use case
4. **Post-processing**: Similarity filtering, keyword matching
5. **Backward Compatible**: Falls back to direct vector store if RAG fails

