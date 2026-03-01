
### Multi-Query Result Merging: Max-Score Deduplication
- **Choice**: When multiple queries match the same tool, we use the maximum score among all matches (`np.max(scores_matrix, axis=0)`).
- **Rationale**: A tool is highly relevant if it matches ANY of the user's sub-queries or variations. Max-score ensures that a strong match for one intent isn't diluted by weaker matches for others. This is standard practice in multi-query retrieval (RAG).
